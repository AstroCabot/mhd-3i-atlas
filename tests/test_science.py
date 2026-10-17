"""Independent checks of scientific units, native selection and harmonization.

Run: python -m unittest discover -s tests -p 'test_science.py' -v
These checks read the immutable native archive and never launch a solver.
"""
import hashlib
import json
import struct
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import brentq

APP = Path(__file__).resolve().parents[1]
SRC = APP.parent / 'mhd_llm'
DATA = APP / 'public/data'
S = json.loads((DATA / 'science.json').read_text())


class ScienceIntegrity(unittest.TestCase):
    def test_final_ct_means_match_native_selected_report(self):
        report = json.loads((SRC / 'codex/results/summary.json').read_text())
        self.assertEqual(report['reference_case'], 'ct156_w30_theta40_phi192')
        native = report['cases'][report['reference_case']]['PN_GTI_weighted_mean']
        for our, key in [('density', 'n'), ('speed', 'v'), ('flux', 'f'), ('incidentFlux', 'f_incident')]:
            self.assertAlmostEqual(S['xray']['models']['codex']['gtiMeans'][our] / native[key], 1, places=7)

    def test_lightcurve_has_exact_native_frames_rates_and_errors(self):
        x = pd.read_csv(SRC / 'argon/data/raw/spacecraft/lightcurve.tsv', sep='\t')
        self.assertEqual(len(S['xray']['observations']), 8)
        self.assertEqual([o['frame'] for o in S['xray']['observations']], x.frame.tolist())
        for i, o in enumerate(S['xray']['observations']):
            self.assertAlmostEqual(o['rate'], x.rate_ct_s.iloc[i], places=7)
            self.assertAlmostEqual(o['error'], x.error_ct_s.iloc[i], places=8)
            self.assertGreater(len(o['intervals']), 0)
        self.assertAlmostEqual(S['xray']['totalPnExposureSeconds'], 21362.2839683, places=3)
        self.assertEqual(S['xray']['rateUnit'], 'counts s⁻¹')
        manuscript=(SRC/'claude/ref/main.txt').read_text()
        self.assertIn('4.29 counts s',manuscript)

    def test_common_gti_normalizations_and_correlations(self):
        x = S['xray']; obs = x['observations']
        weights = np.array([sum(b-a for a,b in o['intervals']) for o in obs])
        rates = np.array([o['rate'] for o in obs])
        for id, m in x['models'].items():
            norm = np.array(m['normalizedFlux'])
            self.assertAlmostEqual(float(np.average(norm, weights=weights)), 1, places=7, msg=id)
            self.assertAlmostEqual(float(np.average(m['rateScaledProxy'], weights=weights)) / np.average(rates, weights=weights), 1, places=7, msg=id)
            self.assertAlmostEqual(float(np.corrcoef(m['incidentFlux'], rates)[0,1]), m['pearsonR'], places=7)
        self.assertLess(x['models']['claude']['pearsonR'], -.65)

    def test_codex_arrival_clock_has_positive_geometric_delay(self):
        d = pd.read_csv(SRC / 'codex/results/comet_timeseries.csv')
        delay = (d.day-d.comet_emission_day)*86400
        self.assertTrue(np.all((delay > 900) & (delay < 1000)))
        # Separate Horizons vector calculation agrees to <0.2 s with the
        # archived Earth-proxy clock, which accounts for a slightly different
        # observer epoch. The time offset is not hours or a fitted phase shift.
        c = pd.read_csv(SRC / 'codex/observations/ephemeris_comet.tsv', sep='\t')
        e = pd.read_csv(SRC / 'argon/data/raw/ephemeris/earth.csv')
        t = d.comet_emission_day.to_numpy()+60980
        cp = np.column_stack([np.interp(t,c.mjd_utc,c[k])for k in ('x_au','y_au','z_au')])
        ep = np.column_stack([np.interp(t,e.JD_UT-2400000.5,e[k])for k in ('x_au','y_au','z_au')])
        physical_delay = np.linalg.norm(cp-ep,axis=1)*499.004783836
        self.assertLess(float(np.max(abs(physical_delay-delay))), .2)

    def test_equal_spacecraft_metric_samples_and_rmse_recomputation(self):
        for craft in S['validation']['spacecraft']:
            obs=np.array(craft['observed']['speed'],float)
            models={id:np.array(m['speed'],float)for id,m in craft['models'].items()}
            mask=np.isfinite(obs)&(obs>0)
            for a in models.values():mask &= np.isfinite(a)&(a>0)
            self.assertGreater(int(mask.sum()), 350)
            for id,a in models.items():
                metric=craft['metrics'][id]
                self.assertEqual(metric['speedN'],int(mask.sum()))
                self.assertAlmostEqual(float(np.sqrt(np.mean((a[mask]-obs[mask])**2))),metric['speedRmse'],places=5)

    def test_comet_physical_flux_units(self):
        # Interpolating n and v separately creates small product differences;
        # away from shocks, n*v*1e5 must agree with the stored physical flux.
        for id in ('argon','codex','claude','enlil'):
            m=S['comet']['series'][id]
            n,v,f=(np.array(m[k],float)for k in ('density','speed','flux'))
            ok=np.isfinite(n)&np.isfinite(v)&np.isfinite(f)
            self.assertGreater(int(ok.sum()),90)
            self.assertLess(float(np.median(abs(n[ok]*v[ok]*1e5/f[ok]-1))), .003)

    def test_animation_shared_shape_time_and_missing_mask(self):
        a=S['animation'];t=np.array(a['timeMjd'])
        self.assertEqual(len(t),32)
        np.testing.assert_allclose(np.diff(t),.25)
        self.assertEqual(a['extentAu'],[-2.4,2.4,-2.4,2.4])
        for id in ('argon','codex','claude'):
            d=json.loads((DATA/f'solarwind-{id}.json').read_text())
            self.assertEqual(d['width'],128);self.assertEqual(d['height'],128)
            self.assertEqual(d['timeMjd'],a['timeMjd'])
            self.assertEqual(np.shape(d['flux']),(32,128*128))
            self.assertEqual(np.shape(d['contrast']),(32,128*128))
            self.assertEqual(d['flux'][0][0],0)  # outside the circular domain
            self.assertGreater(sum(x>0 for x in d['flux'][0]),11000)
            self.assertLess((DATA/f'solarwind-{id}.json').stat().st_size,8_000_000)

    def test_encoded_ct_frame_matches_native_flux_and_orientation(self):
        # Independent bilinear native sampling at a non-axis pixel detects
        # transposition, sign, time-index and units errors simultaneously.
        d=json.loads((DATA/'solarwind-codex.json').read_text())
        case=SRC/'codex/results/ct156_w30_theta40_phi192'
        schedule=pd.read_csv(case/'snapshots.csv')
        t=S['animation']['timeMjd'][0]-60980
        hi=int(np.searchsorted(schedule.day,t,side='right'));lo=hi-1
        x=np.load(case/'ecliptic_x_au.npy');y=np.load(case/'ecliptic_y_au.npy')
        axis=np.linspace(-2.4,2.4,128);iy,ix=83,92
        native=[]
        for i in [lo,hi]:
            values=np.load(case/schedule.file.iloc[i])
            native.append(float(RegularGridInterpolator((y,x),values)([[axis[iy],axis[ix]]])[0]))
        weight=(t-schedule.day.iloc[lo])/(schedule.day.iloc[hi]-schedule.day.iloc[lo])
        expected=(1-weight)*native[0]+weight*native[1]
        code=d['flux'][0][iy*128+ix]
        actual=10**(3+(code-1)/5000)
        self.assertLess(abs(actual/expected-1),.00025)
        contrast=10**(3+(d['contrast'][0][iy*128+ix]-1)/5000)
        self.assertLess(abs(contrast/(expected*(axis[iy]**2+axis[ix]**2))-1),.00025)

    def test_argon_native_constant_latitude_projection(self):
        # Solve the actual conical geometry independently of the builder's
        # analytic inverse. This detects treating the native shell as a plane.
        d=json.loads((DATA/'solarwind-argon.json').read_text())
        R=np.array(json.loads((SRC/'codex/observations/coordinate_system.json').read_text())['ecliptic_to_solar_equatorial_matrix'])
        axis=np.linspace(-2.4,2.4,128);iy,ix=83,92
        xe,ye=axis[ix],axis[iy];lat=np.deg2rad(-6.455)
        def residual(ze):
            h=R@np.array([xe,ye,ze])
            return h[2]/np.linalg.norm(h)-np.sin(lat)
        ze=brentq(residual,-5,5);h=R@np.array([xe,ye,ze])
        rad=np.linalg.norm(h);phi=np.arctan2(h[1],h[0])%(2*np.pi)
        paths=sorted((SRC/'argon/outputs/runs').glob('model3_assimilated_slice_*.bin'))
        native_times=[];planes=[]
        for p in paths:
            with p.open('rb')as f:
                native_times.append(struct.unpack('d',f.read(8))[0])
                planes.append(np.frombuffer(f.read(),np.float32).reshape(4,160,180)[2])
        t=S['animation']['timeMjd'][0];hi=int(np.searchsorted(native_times,t,side='right'));lo=hi-1
        r=.1+(np.arange(160)+.5)*2.3/160;p=(np.arange(180)+.5)*2*np.pi/180
        f=[float(RegularGridInterpolator((r,p),planes[i])([[rad,phi]])[0])for i in [lo,hi]]
        w=(t-native_times[lo])/(native_times[hi]-native_times[lo]);expected=(1-w)*f[0]+w*f[1]
        code=d['flux'][0][iy*128+ix];actual=10**(3+(code-1)/5000)
        self.assertLess(abs(actual/expected-1),.00025)
        code=d['contrast'][0][iy*128+ix];contrast=10**(3+(code-1)/5000)
        self.assertLess(abs(contrast/(expected*rad**2)-1),.00025)
        self.assertIn('conical',S['animation']['models']['argon']['nativePlane'])

    def test_argon_and_claude_native_means_retained_with_qualifications(self):
        a=json.loads((SRC/'argon/outputs/summary_results.json').read_text())
        native=a['mhd_runs']['res_fine_224x48x240']['pn_gti']['flux_rel_mean_cm2s']
        extracted=next(r['incidentFluxPnMean']for r in S['benchmarks']['nativeConvergence']['argon']if r['run']=='res_fine_224x48x240')
        self.assertAlmostEqual(extracted/native,1,places=8)
        self.assertIn('clock',S['homogenization']['nativeMeans'])
        self.assertRegex(S['animation']['models']['argon']['qualification'],r'224(?:-cell)? fine')
        self.assertIn('radial',S['animation']['models']['claude']['definition'])

    def test_provenance_all_generated_source_hashes_still_match(self):
        self.assertGreater(len(S['provenance']),140)
        for row in S['provenance']:
            p=SRC/row['path'];digest=hashlib.sha256()
            with p.open('rb')as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
            self.assertEqual(p.stat().st_size,row['bytes'],row['path'])
            self.assertEqual(digest.hexdigest(),row['sha256'],row['path'])


if __name__=='__main__':
    unittest.main()
