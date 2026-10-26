#!/usr/bin/env python3
"""Build the audit article and figures from preserved experiment artifacts.

Writes only inside this report directory. Never imports or executes model code.
Raw transcript access is needed only for --collect; the article can be rebuilt
from the bundled derived files without the private session archive.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DERIVED = HERE / 'derived'
FIGURES = HERE / 'figures'
for directory in (DERIVED, FIGURES):
    directory.mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', str(HERE / '.mplcache'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

AGENTS = ('Argon', 'Claude', 'Codex')
COLORS = {'collaborative': '#147d85', 'competitive': '#b85e36'}
MODEL_ORDER = [f'{setting}_{name.lower()}' for name in AGENTS
               for setting in ('collaborative', 'competitive')]
NAMES = {key: key.split('_')[1].title() for key in MODEL_ORDER}
LABELS = {key: NAMES[key] + (' · cooperation' if key.startswith('collaborative')
                            else ' · competition') for key in MODEL_ORDER}
LABELS.update(nasa_ccmc_ambient='NASA ENLIL ambient', persistence_24h='Prior-day persistence')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def collect_effort():
    claude = Path.home() / '.claude/projects/-mnt-c-Users-cabot-OneDrive-Documents-Research-Cambridge-X3I'
    argon = Path.home() / '.gemini/antigravity-cli/brain'
    configs = [
        ('collaborative', 'Argon', '2026-10-16T22:32:09Z', '2026-10-17T07', [
            'b3d3df79-0b74-4e57-8d1f-8f7268882191', '8adf310f-c9cf-42ef-a977-86a233e679f1',
            'fc6f5fce-dcf5-4681-a158-510dac649666', '4cce4343-a01f-4d6d-b12e-9ee5e4bd0a9d']),
        ('competitive', 'Argon', '2026-10-18T11:42:36Z', '2026-10-19T00', [
            'e646cea4-8a18-476e-8b69-d32559e8a7b1', 'c0417340-7d5b-4be7-84c6-fb45945a1602',
            '62eb31f3-f5ec-485b-a066-88d89f6dfd09', 'cb0e1e65-5e10-4dd8-a13b-4ed730b85df8']),
        ('collaborative', 'Claude', '2026-10-16T22:32:57.935Z', '2026-10-17T07', ['c4794a53-4881-4aa9-8b9b-7c033457fa8b']),
        ('competitive', 'Claude', '2026-10-18T11:44:03.292Z', '2026-10-19T00', ['e27f95b8-a8f0-48aa-9384-f471118fd435']),
        ('collaborative', 'Codex', '2026-10-16T22:32:24.914Z', '2026-10-17T07', ['01a146ba', '01a146d8', '01a146d9']),
        ('competitive', 'Codex', '2026-10-18T11:42:09.585Z', '2026-10-19T00', ['01a14ec7', '01a14ed1', '01a14ed2']),
    ]
    rows, curves, sources = [], [], []
    for setting, agent, start, end, ids in configs:
        if agent == 'Argon':
            files = [argon / sid / '.system_generated/logs/transcript.jsonl' for sid in ids]
        elif agent == 'Claude':
            files = [claude / (ids[0] + '.jsonl')] + sorted((claude / ids[0]).rglob('*.jsonl'))
        else:
            day = '16' if setting == 'collaborative' else '18'
            files = [p for p in (Path.home() / f'.codex/sessions/2026/10/{day}').glob('*.jsonl')
                     if any(sid in p.name for sid in ids)]
        totals, usage, events = Counter(), {}, []
        active, last_time = 0, start
        thinking_words, thinking_blocks = 0, 0
        for path in files:
            used, last_usage, last_event = False, {}, None
            data = path.read_bytes()
            for line in data.splitlines():
                d = json.loads(line)
                time = d.get('timestamp', d.get('created_at', ''))
                if not (time >= start[:19] and time < end):
                    continue
                if agent == 'Argon':
                    if d.get('type') != 'PLANNER_RESPONSE':
                        continue
                    used = True
                    for key in ('input_tokens', 'cache_read_tokens', 'output_tokens'):
                        totals[key] += d.get(key, 0) or 0
                    events.append((time, d.get('output_tokens', 0) or 0))
                    if d.get('thinking'):
                        thinking_blocks += 1
                        thinking_words += len(d['thinking'].split())
                elif agent == 'Claude':
                    m = d.get('message', {})
                    if d.get('type') != 'assistant' or not isinstance(m, dict) or not m.get('usage'):
                        continue
                    used = True
                    # Global ID de-duplication prevents inherited cross-file copies.
                    previous = usage.get(m['id'])
                    if previous is None or (time, m['usage'].get('output_tokens',0)) >= (previous[0], previous[1].get('output_tokens',0)):
                        usage[m['id']] = (time, m['usage'])
                else:
                    q = d.get('payload', {})
                    if d.get('type') != 'event_msg' or q.get('type') != 'token_count' or not q.get('info'):
                        continue
                    used = True
                    current = q['info']['total_token_usage']
                    diff = current.get('output_tokens', 0) - last_usage.get('output_tokens', 0)
                    if diff < 0:
                        raise ValueError('Unexpected counter reset')
                    events.append((time, diff))
                    last_usage, last_event = current, time
                last_time = max(last_time, time)
            if agent == 'Codex':
                totals.update(last_usage)
            if used:
                active += 1
                sources.append({'agent': agent, 'setting': setting, 'session_file': path.name,
                                'session_id': path.parent.parent.parent.name if agent == 'Argon' else None,
                                'sha256': hashlib.sha256(data).hexdigest(), 'cutoff': end})
        if agent == 'Claude':
            for time, u in usage.values():
                for key in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                    totals[key] += u.get(key, 0) or 0
                totals['reasoning_output_tokens'] += u.get('output_tokens_details', {}).get('thinking_tokens', 0) or 0
                events.append((time, u.get('output_tokens', 0) or 0))
        fresh = (totals['input_tokens'] - totals['cached_input_tokens'] + totals['output_tokens']) if agent == 'Codex' else (
            totals['input_tokens'] + totals['cache_creation_input_tokens'] + totals['output_tokens'])
        key = f'{setting}_{agent.lower()}'
        elapsed = (stamp(last_time) - stamp(start)).total_seconds() / 3600
        row = {'model': key, 'agent': agent, 'setting': setting, 'subagents': active - 1,
               'output_tokens': totals['output_tokens'], 'non_cache_read_tokens': fresh,
               'reasoning_tokens': totals['reasoning_output_tokens'] if agent != 'Argon' else None,
               'observed_span_h': elapsed, 'first_utc': start, 'last_utc': last_time,
               'thinking_summary_words': thinking_words if agent == 'Argon' else None,
               'usage': dict(totals)}
        rows.append(row)
        cumulative = 0
        for time, count in sorted(events):
            cumulative += count
            curves.append({'model': key, 'utc': time, 'elapsed_h': (stamp(time)-stamp(start)).total_seconds()/3600,
                           'output_tokens_cumulative': cumulative})
        assert cumulative == totals['output_tokens'], (key, cumulative, totals)
    # Delivery timestamps, distinct from last cleanup/subagent usage.
    delivery_h = {'collaborative_argon': 1.3492, 'competitive_argon': 4.015,
                  'collaborative_claude': 4.704, 'competitive_claude': 4.5131,
                  'collaborative_codex': 7.9172, 'competitive_codex': None}
    for row in rows:
        row['delivery_h'] = delivery_h[row['model']]
        row['plot_elapsed_h'] = delivery_h[row['model']] or row['observed_span_h']
    dump(DERIVED/'effort.json', {'records': rows, 'sources': sources,
         'method': 'Task-scoped root and delegated records. Claude deduplicated globally by message ID, keeping the chronologically latest usage record (output count breaks ties); '
                   'Codex final cumulative counters per session. Reasoning is a subset of output. '
                   'No raw transcript content is bundled. Delivery time and last recorded activity are distinct.'})
    pd.DataFrame([{k:v for k,v in row.items() if k!='usage'} for row in rows]).to_csv(DERIVED/'effort.csv', index=False)
    pd.DataFrame(curves).to_csv(DERIVED/'token_curve.csv', index=False)


def save_figure(fig, name):
    fig.savefig(FIGURES/f'{name}.svg', bbox_inches='tight', facecolor='white')
    fig.savefig(FIGURES/f'{name}.png', bbox_inches='tight', dpi=210, facecolor='white')
    fig.savefig(FIGURES/f'{name}.pdf', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def figures(effort):
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'axes.labelsize':10,
        'axes.spines.top':False, 'axes.spines.right':False, 'axes.spines.left':False,
        'axes.edgecolor':'#bfc9cd', 'text.color':'#213540', 'axes.labelcolor':'#213540',
        'xtick.color':'#53656d', 'ytick.color':'#213540', 'svg.fonttype':'none'})
    rows = {r['model']:r for r in effort}
    fig, axes = plt.subplots(1,2,figsize=(10.4,3.6), gridspec_kw={'wspace':0.3})
    fig.subplots_adjust(bottom=.26)
    for ax, key, title, maximum in [(axes[0], 'plot_elapsed_h', 'Elapsed hours', 12.5),
                                   (axes[1], 'output_tokens', 'Generated tokens, millions', 3.1)]:
        for j, agent in enumerate(AGENTS):
            for setting, delta in [('collaborative',-.17),('competitive',.17)]:
                val=rows[f'{setting}_{agent.lower()}'][key]
                if key=='output_tokens': val/=1e6
                ax.barh(j+delta,val,height=.28,color=COLORS[setting],zorder=3)
                marker='*' if key=='plot_elapsed_h' and agent=='Codex' and setting=='competitive' else ''
                ax.text(val+.06,j+delta,f'{val:.2f}{marker}',va='center',fontsize=9)
        ax.set(yticks=range(3),yticklabels=AGENTS,xlim=(0,maximum),xlabel=title)
        ax.invert_yaxis();ax.grid(axis='x',alpha=.2,zorder=0);ax.tick_params(axis='y',length=0)
    fig.legend(handles=[plt.Rectangle((0,0),1,1,color=COLORS[s],label=l) for s,l in [
        ('collaborative','Cooperation'),('competitive','Competition')]],loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,1.08))
    fig.text(.02,.015,'* Codex competition: last subagent activity; final delivery remained incomplete.\nTokens include code, tool arguments and reasoning; they are not a price or energy measure.',fontsize=8,color='#53656d')
    save_figure(fig,'effort')

    pairs=pd.read_csv(DERIVED/'matched_monitor_pairs.csv')
    pairs['time']=pd.to_datetime(pairs.utc,utc=True)
    fig,axes=plt.subplots(3,2,figsize=(11.0,7.5),sharex=True,sharey='col',gridspec_kw={'hspace':.2,'wspace':.16})
    for i,agent in enumerate(AGENTS):
        for j,probe in enumerate(('wind','stereo_a')):
            ax=axes[i,j]
            obs=pairs[(pairs.model=='nasa_ccmc_ambient')&(pairs.probe==probe)]
            ax.plot(obs.time,obs.observed_bulk_flux_cm2_s/1e8,color='#172c36',lw=1.2,label='Observed',zorder=5)
            ax.plot(obs.time,obs.model_bulk_flux_cm2_s/1e8,color='#9ca7ad',lw=1.1,label='NASA ambient',zorder=1)
            for setting in ('collaborative','competitive'):
                d=pairs[(pairs.model==f'{setting}_{agent.lower()}')&(pairs.probe==probe)]
                ax.plot(d.time,d.model_bulk_flux_cm2_s/1e8,color=COLORS[setting],lw=1.45,
                        ls='-' if setting=='collaborative' else '--',label='Cooperation' if setting=='collaborative' else 'Competition')
            ax.axvspan(pd.Timestamp('2025-12-03T12:04:07Z'),pd.Timestamp('2025-12-04T10:11:54Z'),color='#e9d6b4',alpha=.28,zorder=0)
            ax.grid(alpha=.14);ax.set_ylim(bottom=0)
            if i==0:ax.set_title('Wind / near Earth' if probe=='wind' else 'STEREO-A',fontweight='bold',pad=12)
            if j==0:ax.set_ylabel(agent+'\nFlux / 10⁸ cm⁻² s⁻¹')
            ax.xaxis.set_major_locator(mdates.DayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=4,bbox_to_anchor=(.5,1.015),frameon=False,fontsize=9)
    fig.text(.04,.005,'Identical hourly observations, December 1–5, 2025 UTC. Shading marks the science interval.\nNominal reconstructions have different training histories; these curves are not a blinded prediction test.',fontsize=8,color='#53656d')
    save_figure(fig,'monitor_comparison')

    # Common science-window means from native saved comet samples.
    window=(61012.5028587963,61013.4249305556)
    def utc_mjd(values):
        return np.asarray([value.timestamp()/86400+40587 for value in pd.to_datetime(values,utc=True)])
    native=[]
    p=ROOT/'mhd_llm/argon/outputs/runs/res_fine_224x48x240_probes.tsv';d=pd.read_csv(p,sep='\t');d=d[d.probe=='comet']
    native.append(('collaborative_argon',d.mjd_utc.to_numpy(),d.n_cm3.to_numpy(),d.vmag_kms.to_numpy(),p))
    p=ROOT/'mhd_llm/claude/figs/timeseries_3i_atlas.csv';d=pd.read_csv(p)
    native.append(('collaborative_claude',utc_mjd(d.utc),d['n_1°'].to_numpy(),d['v_1°'].to_numpy(),p))
    p=ROOT/'mhd_llm/codex/results/comet_timeseries.csv';d=pd.read_csv(p)
    native.append(('collaborative_codex',utc_mjd(d.comet_emission_utc),d.density_cm3.to_numpy(),d.speed_heliocentric_kms.to_numpy(),p))
    p=ROOT/'mhd_llm_adversarial/argon/results/ts_argon_high.csv';d=pd.read_csv(p)
    native.append(('competitive_argon',d.mjd_utc.to_numpy(),d.comet_np.to_numpy(),d.comet_vmag.to_numpy(),p))
    p=ROOT/'mhd_llm_adversarial/claude/products/timeseries_3I.csv';d=pd.read_csv(p)
    native.append(('competitive_claude',utc_mjd(d.iso),d.n.to_numpy(),d.v.to_numpy(),p))
    p=ROOT/'mhd_llm_adversarial/codex/outputs/products/comet_timeseries.csv';d=pd.read_csv(p)
    native.append(('competitive_codex',d.mjd_utc.to_numpy(),d.n_cm3.to_numpy(),d.speed_kms.to_numpy(),p))
    p=ROOT/'outputs/enlil_3i_dec4_2025/Jan_Deca_120925_SH_1_evo_3I-Atlas1_20251001T00.dat'
    a=np.loadtxt(p,comments='#',usecols=(0,5,7,8,9));native.append(('nasa_full_N_proxy',a[:,0],a[:,1],np.sqrt((a[:,2:5]**2).sum(axis=1)),p))
    fluxrows=[]
    for model,t,n,v,p in native:
        assert np.all(np.diff(t)>0), model
        assert t.min()<=window[0] and t.max()>=window[1],model
        x=np.r_[window[0],t[(t>window[0])&(t<window[1])],window[1]]
        f=n*v*1e5
        mean=float(np.trapezoid(np.interp(x,t,f),x)/(window[1]-window[0]))
        fluxrows.append({'model':model,'mean_bulk_flux_cm2_s':mean,'source':str(p.relative_to(ROOT)),
                         'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    dump(DERIVED/'common_comet_flux.json',{'window_mjd':window,'duration_seconds':79667,
         'definition':'Average instantaneous n*full-vector-speed, piecewise-linear in physical UTC. '
                      'No GTI weighting or common light-time correction. NASA reported N is unscaled proxy.',
         'records':fluxrows})
    pd.DataFrame(fluxrows).to_csv(DERIVED/'common_comet_flux.csv',index=False)
    fig,ax=plt.subplots(figsize=(9.6,3.65))
    fig.subplots_adjust(bottom=.26)
    for i,agent in enumerate(AGENTS):
        for setting,offset in [('collaborative',-.14),('competitive',.14)]:
            val=next(r['mean_bulk_flux_cm2_s'] for r in fluxrows if r['model']==f'{setting}_{agent.lower()}')/1e8
            ax.scatter(val,i+offset,color=COLORS[setting],s=75,zorder=3)
            ax.text(val+.035,i+offset,f'{val:.3f}',va='center',fontsize=9)
    nasa=fluxrows[-1]['mean_bulk_flux_cm2_s']/1e8
    ax.axvline(nasa,color='#7d898f',ls=':',lw=1.4)
    ax.text(nasa-.025,2.52,'NASA full\nN proxy 0.447',ha='right',va='bottom',color='#53656d',fontsize=8)
    ax.set(yticks=range(3),yticklabels=AGENTS,xlim=(0,2.3),ylim=(-.55,2.65),xlabel='Mean bulk flux / 10⁸ cm⁻² s⁻¹')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.2);ax.tick_params(axis='y',length=0)
    fig.legend(handles=[plt.Line2D([],[],marker='o',ls='',color=COLORS[s],label=l) for s,l in [
        ('collaborative','Cooperation'),('competitive','Competition')]],loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,1.04))
    fig.text(.02,.015,'Same physical UTC interval: December 3 12:04:07 to December 4 10:11:54.\nThese are conditional outputs, not confidence intervals. Argon competition has serious provenance limitations.',fontsize=8,color='#53656d')
    save_figure(fig,'comet_flux')


def build():
    effort=json.loads((DERIVED/'effort.json').read_text())['records']
    figures(effort)
    metrics=pd.read_csv(DERIVED/'matched_monitor_metrics.csv')
    metrics=metrics[metrics.window=='Dec1_to_Dec5_00UTC']
    table=[]
    for model in MODEL_ORDER+['nasa_ccmc_ambient','persistence_24h']:
        row={'label':LABELS[model],'model':model}
        for probe in ('wind','stereo_a'):
            r=metrics[(metrics.model==model)&(metrics.probe==probe)].iloc[0]
            row[probe+'_rmse']=f'{r.bulk_flux_cm2_s_rmse/1e8:.3f}'
            row[probe+'_r']='—' if pd.isna(r.bulk_flux_cm2_s_pearson_r) else f'{r.bulk_flux_cm2_s_pearson_r:.3f}'.replace('-', '−')
        table.append(row)
    environment=Environment(loader=FileSystemLoader(HERE),autoescape=select_autoescape(['html','j2']))
    def embedded(name):
        return 'data:image/svg+xml;base64,'+base64.b64encode((FIGURES/(name+'.svg')).read_bytes()).decode()
    article=environment.get_template('article.html.j2').render(
        effort={r['model']:r for r in effort},accuracy=table,figure=embedded,
        quotes=json.loads((DERIVED/'quotes.json').read_text())['quotes'])
    (HERE/'index.html').write_text(article)
    print(json.dumps({'html_bytes':len(article.encode()),'figures':3,'accuracy_rows':len(table)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--collect',action='store_true');parser.add_argument('--collect-only',action='store_true')
    args=parser.parse_args()
    if args.collect or args.collect_only:collect_effort()
    if not args.collect_only:build()
