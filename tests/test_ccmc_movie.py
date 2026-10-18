"""Independent unit, orientation and temporal-support checks for the CCMC movie."""
from pathlib import Path
import hashlib
import json
import sys
import unittest

import numpy as np
import pandas as pd
from scipy.io import netcdf_file
from scipy.interpolate import RegularGridInterpolator

APP=Path(__file__).resolve().parents[1]
SOURCE=APP.parent/'mhd_llm'
sys.path.insert(0,str(APP/'scripts'))
import prepare_ccmc_movie as ccmc


class CCMCMovie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((APP/'public/data/ccmc-movie-provenance.json').read_text())
        cls.manifest=json.loads((APP/'public/data/animation-v2.json').read_text())

    def test_common_display_parameters_and_native_coverage(self):
        model=self.manifest['models']['enlil']
        self.assertEqual(model['solverDimensions'],[576,24,90])
        self.assertEqual(model['nominalCadenceHours'],6)
        self.assertEqual(self.receipt['block'],0)
        self.assertEqual([row['index'] for row in self.receipt['snapshots']],list(range(228,261)))
        self.assertLessEqual(model['usedNativeTimeMjd'][0],self.manifest['startMjd'])
        self.assertGreaterEqual(model['usedNativeTimeMjd'][-1],self.manifest['endMjd'])
        self.assertGreater(model['actualCadenceHours']['minimum'],5.8)
        self.assertLess(model['actualCadenceHours']['maximum'],6.2)
        self.assertEqual(model['frameSequence']['timeMjd'],self.manifest['models']['claude']['frameSequence']['timeMjd'])
        self.assertFalse(model['frameSequence']['supportEpochsAreNativeSolverOutputs'])
        for media in model['media'].values():
            self.assertEqual([media['width'],media['height'],media['fps'],media['frames'],media['durationSeconds']],[768,768,30,1440,48])
        self.assertEqual(model['sourceReceiptSha256'],hashlib.sha256((APP/'public/data/ccmc-movie-provenance.json').read_bytes()).hexdigest())

    def test_raw_grid_oracle_detects_density_and_coordinate_errors(self):
        # Build the archive longitude from an Earth-aligned orthogonal basis,
        # independently of the movie's subtraction of solar azimuth angles.
        source=SOURCE/'claude/ref/ccmc/raw/tim/tim.0254.nc'
        with netcdf_file(source,'r',mmap=False) as nc:
            v=nc.variables;epoch=float(v['TIME'].data)/86400+60949
            R=np.array(json.loads((SOURCE/'codex/observations/coordinate_system.json').read_text())['ecliptic_to_solar_equatorial_matrix'])
            earth=pd.read_csv(SOURCE/'argon/data/raw/ephemeris/earth.csv')
            E=np.array([np.interp(epoch,earth.JD_UT-2400000.5,earth[key]) for key in ['x_au','y_au','z_au']])@R.T
            xhat=np.array([E[0],E[1],0]);xhat/=np.linalg.norm(xhat)
            yhat=np.cross([0,0,1],xhat)
            xyz=np.array([.84,1.12,0]);solar=R@xyz
            radius=np.linalg.norm(solar)
            longitude=(np.arctan2(np.dot(solar,yhat),np.dot(solar,xhat))+np.pi)%(2*np.pi)
            theta=np.arccos(solar[2]/radius)
            density=v['D'].data[0].astype(float)/1.67239e-27/1e6/1.2
            speed=np.sqrt(sum(v[key].data[0].astype(float)**2 for key in ['V1','V2','V3']))
            flux=density*speed*100
            p=v['X3'].data[0].astype(float);r=v['X1'].data[0].astype(float)/1.495978707e11;t=v['X2'].data[0].astype(float)
            pp=np.r_[p[-1]-2*np.pi,p,p[0]+2*np.pi]
            flux=np.concatenate([flux[-1:],flux,flux[:1]],axis=0)
            expected=float(RegularGridInterpolator((pp,t,r),flux)([[longitude,theta,radius]])[0])
        times,fields,_,_=ccmc.load_native(np.array([[xyz[0]]]),np.array([[xyz[1]]]))
        actual=float(fields[np.argmin(abs(times-epoch))][0,0])
        self.assertLess(abs(actual/expected-1),2e-7)

    def test_source_receipts_and_compact_inputs(self):
        for row in self.receipt['snapshots']:
            self.assertEqual(row['sourceBytes'],99541956)
            self.assertEqual(len(row['sourceSha256']),64)
            self.assertEqual(hashlib.sha256((APP/row['productPath']).read_bytes()).hexdigest(),row['productSha256'])
            density=[check for check in row['primitiveChecks'] if check['field']=='D']
            self.assertEqual(len(density),3)
            for check in density:self.assertLess(check['absoluteError']/abs(check['reference']),1e-4)


if __name__=='__main__':unittest.main()
