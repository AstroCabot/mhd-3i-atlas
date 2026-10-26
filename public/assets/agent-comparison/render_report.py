#!/usr/bin/env python3
"""Print the local article to PDF and add restrained page numbers."""
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

import pymupdf

HERE=Path(__file__).resolve().parent
cache=Path.home()/'.cache/ms-playwright'
candidates=list(cache.glob('chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell'))
if not candidates:
    candidates=list(cache.glob('chromium-*/chrome-linux64/chrome'))
if not candidates:
    raise SystemExit('Set up a Chromium binary or use browser Print → Save as PDF.')
browser=sorted(candidates)[-1]
with tempfile.TemporaryDirectory(prefix='mhd-report-browser-') as profile:
    command=[str(browser),'--headless','--no-sandbox','--disable-dev-shm-usage',
             '--disable-background-networking','--disable-extensions','--disable-sync',
             '--no-pdf-header-footer','--timeout=12000',f'--user-data-dir={profile}',
             f'--print-to-pdf={HERE/"report.pdf"}',(HERE/'index.html').as_uri()]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stdout,stderr=process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)
        process.communicate(timeout=5)
        raise SystemExit('Chromium exceeded its render timeout; output not accepted.')
    if process.returncode:
        raise SystemExit(stderr.decode(errors='replace')[-2000:])
doc=pymupdf.open(HERE/'report.pdf')
doc.set_metadata({'title':'When AI agents model the solar wind',
                  'subject':'An audit of cooperation, competition, computation and validation across six autonomous MHD research runs',
                  'creator':'HTML article rendered with Chromium; figures generated with Matplotlib',
                  'keywords':'MHD, solar wind, autonomous agents, cooperation, competition, research audit'})
for i,page in enumerate(doc):
    page.insert_textbox(pymupdf.Rect(42,page.rect.height-28,page.rect.width-42,page.rect.height-12),
                        f'{i+1} / {len(doc)}',fontname='helv',fontsize=8,align=2,color=(.36,.43,.46))
target=HERE/'report.numbered.pdf';doc.save(target,garbage=4,deflate=True);n=len(doc);doc.close()
target.replace(HERE/'report.pdf')
print(json.dumps({'pages':n,'pdf_bytes':(HERE/'report.pdf').stat().st_size}))
