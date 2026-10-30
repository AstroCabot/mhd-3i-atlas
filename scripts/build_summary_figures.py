"""Render static teaching figures from archived ephemerides and real GONG/WSA maps.

Rendering requires numpy, matplotlib and astropy. Pages uses the committed figures
and receipts, so its build needs no plotting packages, network or research solver.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyArrowPatch
import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'public/assets/summary'
INPUTS = BASE / 'figure-inputs'
OUTPUT = BASE / 'figures'
EPOCH = '2025-12-03T23:00:00.000'
SOURCE_MAPS = {
    'gong-20251125.fits.gz': 'claude/data/gong/mrzqs251125t0004c2304_007.fits.gz',
    'wsa-corona-20251125.fits': 'claude/data/wsa_ccmc/wsa_202511250004R000_gong_z.fits',
    'wsa-speed-20251125.fits': 'claude/data/wsa_ccmc/vel/vel_202511250004R000_gongz.fits',
}
INK, MUTED, GRID = '#26363a', '#58666a', '#dbe0de'
TEAL, RUST, GOLD = '#267779', '#a34b39', '#b78326'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_receipt(path):
    return {'url': '/' + path.relative_to(ROOT / 'public').as_posix(),
            'bytes': path.stat().st_size, 'sha256': digest(path)}


def import_inputs(source):
    INPUTS.mkdir(parents=True, exist_ok=True)
    origins, rows = [], []
    for name, original in SOURCE_MAPS.items():
        shutil.copy2(source / original, INPUTS / name)
        origins.append({'sourcePath': original, 'sha256': digest(source / original)})
    for name in ['3i_atlas', 'stereo_a', 'solar_orbiter', 'earth', 'wind', 'ace', 'mercury', 'venus', 'mars']:
        path = source / 'claude/data/ephem' / (name + '.csv')
        with path.open(newline='') as stream:
            matches = [row for row in csv.DictReader(stream) if row['utc'] == EPOCH]
        if len(matches) != 1:
            raise ValueError(f'The geometry must use one exact archived epoch: {path}')
        row = matches[0]
        rows.append({'body': name, **{key: row[key] for key in
                    ['utc', 'r_au', 'ecl_lon_deg', 'ecl_lat_deg', 'hgi_lat_deg']}})
        origins.append({'sourcePath': 'claude/data/ephem/' + path.name, 'sha256': digest(path),
                        'extraction': 'One exact archived row; no interpolation or trajectory rerun.'})
    with (INPUTS / 'positions.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    (INPUTS / 'provenance.json').write_text(json.dumps({
        'epochUtc': EPOCH, 'positionSource': 'Archived JPL Horizons-derived tables from the original Claude research workspace.',
        'projection': 'Sun-centered fixed-J2000 ecliptic x/y, viewed from ecliptic north. Positions are projected, not moved into the plane.',
        'originalSources': origins,
        'credit': 'GONG observations: NSF National Solar Observatory / NISP / GONG. WSA 5.4 maps: NASA CCMC/iSWA. Geometry: NASA/JPL Horizons.',
        'originalDataUrls': ['https://gong.nso.edu/data/magmap/QR/zqs/', 'https://iswa.gsfc.nasa.gov/iswa_data_tree/model/solar/WSA5.4/R21.5/'],
    }, indent=2) + '\n')


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK,
                         'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                         'axes.edgecolor': GRID, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'path', 'svg.hashsalt': '3i-summary-static-v1',
                         'savefig.facecolor': 'white', 'figure.facecolor': 'white', 'pdf.fonttype': 42})


def save(fig, name):
    for suffix in ['svg', 'png', 'pdf']:
        metadata = {'Date': None} if suffix == 'svg' else {'CreationDate': None, 'ModDate': None} if suffix == 'pdf' else {}
        fig.savefig(OUTPUT / f'{name}.{suffix}', dpi=190, metadata=metadata)
    plt.close(fig)


def geometry():
    with (INPUTS / 'positions.csv').open(newline='') as stream:
        positions = {row['body']: row for row in csv.DictReader(stream)}
    for row in positions.values():
        radius, lon, lat = (float(row[key]) for key in ['r_au', 'ecl_lon_deg', 'ecl_lat_deg'])
        row['xyz'] = [radius * np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(lon)),
                      radius * np.cos(np.deg2rad(lat)) * np.sin(np.deg2rad(lon)), radius * np.sin(np.deg2rad(lat))]
    fig = plt.figure(figsize=(10.4, 6.15))
    ax = fig.add_axes([.075, .13, .60, .77]); note = fig.add_axes([.73, .15, .255, .71]); note.axis('off')
    ax.set_aspect('equal'); ax.set(xlim=(-2.15, 2.15), ylim=(-1.8, 1.7), xlabel='Ecliptic x / AU', ylabel='Ecliptic y / AU')
    ax.set_xticks([-2, -1, 0, 1, 2]); ax.set_yticks([-1, 0, 1])
    for radius in [1, 2]:
        ax.add_patch(Circle((0, 0), radius, fill=False, ec=GRID, lw=.8, ls='--'))
        label_xy = (-.08, -1.03) if radius == 1 else (-1.40, -1.40)
        ax.text(*label_xy, f'{radius} AU', fontsize=9, color=MUTED,
                bbox={'fc': 'white', 'ec': 'none', 'pad': 1})
    ax.add_patch(Circle((0, 0), .1, fill=False, ec=MUTED, lw=1))
    ax.scatter([0], [0], s=115, color=GOLD, zorder=6, edgecolors='white')
    ax.annotate('Sun', (0, 0), xytext=(8, -16), textcoords='offset points', fontsize=10)
    annotation = {
        '3i_atlas': ('3I/ATLAS', RUST, (-4, 40)), 'stereo_a': ('STEREO-A', TEAL, (-93, -12)),
        'solar_orbiter': ('Solar Orbiter', '#476c99', (-20, 48)), 'earth': ('Earth / L1 region', INK, (28, 0)),
        'mercury': ('Mercury', MUTED, (-64, -20)), 'venus': ('Venus', MUTED, (-45, -15)),
        'mars': ('Mars', MUTED, (11, 0)),
    }
    for name, (label, color, offset) in annotation.items():
        row = positions[name]; x, y = row['xyz'][:2]
        selected = name in ['3i_atlas', 'stereo_a', 'solar_orbiter', 'earth']
        ax.scatter([x], [y], s=54 if selected else 22, color=color, ec='white', lw=.8, zorder=6)
        ax.annotate(f"{label}\n{float(row['r_au']):.2f} AU", (x, y), xytext=offset, textcoords='offset points',
                    fontsize=10 if selected else 9, color=color, va='center', linespacing=1.5,
                    arrowprops={'arrowstyle': '-', 'color': color, 'lw': .8}, zorder=7)
    for name in ['wind', 'ace']:
        ax.scatter(*positions[name]['xyz'][:2], s=10, color=TEAL, zorder=7)
    c, s = positions['3i_atlas'], positions['stereo_a']
    angles = [float(row['ecl_lon_deg']) for row in [s, c]]
    for row in [s, c]:
        ax.plot([0, row['xyz'][0]], [0, row['xyz'][1]], color=GRID, lw=.8, ls=':')
    ax.add_patch(Arc((0, 0), 1.0, 1.0, theta1=min(angles), theta2=max(angles), color=MUTED, lw=1.1))
    mean = np.deg2rad(np.mean(angles))
    ax.text(.62 * np.cos(mean) - .12, .62 * np.sin(mean), f'{abs(angles[1]-angles[0]):.1f}°', color=MUTED, fontsize=10)
    note.text(0, 1, 'Solar latitudes', fontsize=11, weight='bold', va='top')
    note.text(0, .89, 'Latitude relative to the\nSun’s equator', fontsize=10, color=MUTED, va='top', linespacing=1.5)
    for index, (name, label, color) in enumerate([
            ('3i_atlas', '3I/ATLAS', RUST), ('stereo_a', 'STEREO-A', TEAL),
            ('earth', 'Earth', INK), ('solar_orbiter', 'Solar Orbiter', '#476c99')]):
        note.text(0, .72 - index * .10, label, color=color, fontsize=10)
        note.text(.98, .72 - index * .10, f"{float(positions[name]['hgi_lat_deg']):+.2f}°", ha='right', fontsize=10)
    note.text(0, .26, 'STEREO-A is close in latitude,\nbut about 25° away in longitude\nand roughly 0.9 AU closer in.\n\nWind and ACE lie near Earth;\ntheir separation is too small\nto resolve at this scale.', fontsize=9.5,
              color=MUTED, va='top', linespacing=1.6)
    fig.text(.075, .97, 'Where the comet and the measurements were', fontsize=14, weight='bold', va='top')
    fig.text(.075, .925, '3 December 2025, 23:00 UTC · top-down projection from ecliptic north', color=MUTED, fontsize=10)
    fig.text(.075, .025, 'Dashed circles lie 1 and 2 AU from the Sun. The small inner circle is the 0.1 AU model boundary. Symbols are enlarged.', fontsize=9, color=MUTED)
    save(fig, 'geometry')
    return {'epochUtc': EPOCH, 'positions': {name: {'xEclipticAu': row['xyz'][0], 'yEclipticAu': row['xyz'][1],
                     'zEclipticAu': row['xyz'][2], 'radiusAu': float(row['r_au']), 'solarLatitudeDeg': float(row['hgi_lat_deg'])}
                     for name, row in positions.items()}, 'eclipticCometStereoSeparationDeg': abs(angles[1] - angles[0])}


def gong_wsa():
    with fits.open(INPUTS / 'gong-20251125.fits.gz') as hdul:
        field, header = hdul[0].data.copy(), hdul[0].header.copy()
    with fits.open(INPUTS / 'wsa-corona-20251125.fits') as hdul:
        coronal, coronal_header = hdul[0].data.copy(), hdul[0].header.copy()
    with fits.open(INPUTS / 'wsa-speed-20251125.fits') as hdul:
        speed, speed_header = hdul[0].data[1].copy(), hdul[0].header.copy()
    if not (header['FILELIST'] == coronal_header['FILELIST'] == speed_header['FILELIST']):
        raise ValueError('The magnetogram and WSA products must identify the same GONG source')
    fexp, distance = coronal[1].astype(float), coronal[5].astype(float)
    def empirical(f, d):
        return 285 + 625 / (1 + f) ** .22222 * (1 - .8 * np.exp(-(d / 2) ** 2)) ** 3
    error = float(np.max(abs(empirical(fexp, distance) - speed)))
    if error > 3.1e-5:
        raise ValueError('The recorded WSA law does not reproduce the archived velocity plane')
    field_lon = ((np.arange(field.shape[1]) + 1 - header['CRPIX1']) * header['CDELT1'] + header['CRVAL1']) % 360
    field_order = np.argsort(field_lon); field = field[:, field_order]
    field_y = (np.arange(field.shape[0] + 1) + .5 - header['CRPIX2']) * header['CDELT2'] + header['CRVAL2']
    lon = (speed_header['CARRLONG'] + 1 + 2 * np.arange(speed.shape[1])) % 360
    order = np.argsort(lon); speed = speed[:, order]; sorted_lon = lon[order]
    # This date has even-degree centers. Keep their WCS rather than silently
    # shifting the velocity map by one degree; repeat the seam column only.
    speed_edges = np.r_[sorted_lon - 1, sorted_lon[-1] + 1, sorted_lon[-1] + 3]
    periodic_speed = np.column_stack([speed, speed[:, 0]])
    fig = plt.figure(figsize=(10.4, 6.4))
    axs = [fig.add_axes([.09, .56, .76, .30]), fig.add_axes([.09, .13, .76, .30])]
    field_image = axs[0].pcolormesh(np.arange(361), field_y, field, cmap='RdBu_r', vmin=-50, vmax=50, shading='flat', rasterized=True)
    speed_image = axs[1].pcolormesh(speed_edges, np.sin(np.deg2rad(np.linspace(-90, 90, 91))), periodic_speed,
                                  cmap='viridis', vmin=280, vmax=850, shading='flat', rasterized=True)
    for ax in axs:
        ax.set(xlim=(0, 360), ylim=(-1, 1), ylabel='Solar latitude')
        ax.set_xticks(np.arange(0, 361, 60)); ax.set_yticks(np.sin(np.deg2rad([-90, -30, 0, 30, 90])))
        ax.set_yticklabels(['−90°', '−30°', '0°', '+30°', '+90°'])
    axs[0].set_xticklabels([])
    axs[1].set_xlabel('Carrington longitude / degrees')
    axs[0].set_title('A  GONG surface magnetic map · inferred radial field', loc='left', fontsize=11, pad=10, weight='bold')
    axs[1].set_title('B  WSA wind speed at 21.5 solar radii · before any agent adjustment', loc='left', fontsize=11, pad=10, weight='bold')
    cb1 = fig.colorbar(field_image, cax=fig.add_axes([.875, .56, .017, .30]), extend='both')
    cb1.set_label('Radial field / G'); cb1.set_ticks([-50, 0, 50]); cb1.set_ticklabels(['−50', '0', '+50'])
    cb2 = fig.colorbar(speed_image, cax=fig.add_axes([.875, .13, .017, .30]))
    cb2.set_label('Speed / km s⁻¹'); cb2.set_ticks([300, 500, 700, 850])
    fig.text(.09, .98, 'From a surface magnetic map to a wind speed', fontsize=14, weight='bold', va='top')
    fig.text(.09, .925, 'Archived 25 November 2025, 00:04 UTC products · NSO/GONG and NASA CCMC/iSWA WSA 5.4', color=MUTED, fontsize=10)
    fig.text(.09, .025, 'Red and blue are opposite magnetic polarities. The lower panel comes from a coronal model and an empirical speed rule.', fontsize=9, color=MUTED)
    save(fig, 'gong-wsa')
    return {'gongShape': list(field.shape), 'wsaShape': list(speed.shape), 'commonSourceFilelist': header['FILELIST'],
            'gongDisplayLimitGauss': 50, 'gongActualRangeGauss': [float(np.min(field)), float(np.max(field))],
            'nativeWsaSpeedRangeKms': [float(np.min(speed)), float(np.max(speed))],
            'nativeVelocityLaw': speed_header['VELEQN'], 'velocityLawMaximumErrorKms': error,
            'examplesKms': {'f3_d0p2': float(empirical(3, .2)), 'f3_d4': float(empirical(3, 4)), 'f30_d4': float(empirical(30, 4))},
            'wsaLongitudeCentersDeg': sorted_lon.tolist(),
            'mapDisplay': 'Longitude columns sorted to 0–360 degrees with their native WCS; the first WSA column is repeated at the periodic seam. No numerical smoothing. Latitude uses sine latitude in both panels. Strong GONG pixels saturate at ±50 G.'}


def field_and_cme():
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.9), gridspec_kw={'wspace': .20})
    fig.subplots_adjust(left=.035, right=.98, bottom=.22, top=.83)
    left, right = axes
    for ax in axes:
        ax.set_aspect('equal'); ax.axis('off')
    # Snapshot of a kinematic equatorial Parker field: constant radial speed,
    # rotating footpoints, outward-polarity examples. No fitted model or event.
    r = np.linspace(.13, 1.72, 400); omega_r_over_v = 1.0
    for phase in [.3, 1.8, 3.3, 4.8]:
        phi = phase - omega_r_over_v * (r - .13)
        x, y = r * np.cos(phi), r * np.sin(phi)
        left.plot(x, y, color=TEAL, lw=1.9)
        idx = 245
        left.add_patch(FancyArrowPatch((x[idx-5], y[idx-5]), (x[idx+5], y[idx+5]), arrowstyle='-|>',
                                      mutation_scale=11, color=TEAL, lw=1.2))
    left.add_patch(Circle((0, 0), .13, color=GOLD, zorder=5))
    left.add_patch(Arc((0, 0), .67, .67, theta1=25, theta2=120, color=GOLD, lw=1.5))
    theta = np.deg2rad(120)
    left.annotate('', xy=(.335*np.cos(theta), .335*np.sin(theta)), xytext=(.335*np.cos(theta-.16), .335*np.sin(theta-.16)),
                  arrowprops={'arrowstyle': '-|>', 'color': GOLD, 'lw': 1.5})
    left.text(.08, .39, 'Sun rotates', color=GOLD, fontsize=10)
    # Grey arrows show radial bulk motion, not motion tangent to the spiral.
    for angle in [.4, 2.1, 4.0, 5.6]:
        a = np.array([np.cos(angle), np.sin(angle)])
        left.annotate('', xy=1.43*a, xytext=.98*a, arrowprops={'arrowstyle': '-|>', 'color': MUTED, 'lw': 1.5})
    left.set(xlim=(-1.9, 1.9), ylim=(-1.85, 1.85))
    left.set_title('A  Parker spiral: field lines and wind', loc='left', fontsize=11, weight='bold', pad=15)
    left.text(-1.8, -1.88, 'Teal: magnetic field lines at one instant\nGrey: direction of the wind, nearly radial', fontsize=10, color=MUTED, va='top', linespacing=1.5)
    # Generic cone geometry: rays give an angular envelope, while a spherical
    # cloud crossing the inner boundary supplies a finite injection footprint.
    r0, center, cloud_radius, half = .7, 1.2, .6, np.deg2rad(30)
    right.add_patch(Circle((0, 0), r0, fill=False, ec=GRID, lw=1.3))
    for sign in [-1, 1]:
        right.plot([0, 2.15*np.cos(half)], [0, sign*2.15*np.sin(half)], ls='--', color=MUTED, lw=1.1)
    right.add_patch(Circle((center, 0), cloud_radius, facecolor='#f6e7e0', ec=RUST, lw=1.8))
    right.plot([0, 2.15], [0, 0], ls=':', color=MUTED, lw=1)
    right.add_patch(Arc((0, 0), .9, .9, theta1=0, theta2=30, color=RUST, lw=1.3))
    right.text(.46, .13, 'w', color=RUST, fontsize=12)
    patch_half = np.arccos((r0*r0 + center*center - cloud_radius*cloud_radius)/(2*r0*center))
    right.add_patch(Arc((0, 0), 2*r0, 2*r0, theta1=-np.rad2deg(patch_half), theta2=np.rad2deg(patch_half), color=RUST, lw=4))
    right.add_patch(Circle((0, 0), .10, color=GOLD, zorder=5))
    right.annotate('injection boundary\n0.1 AU', (.7*np.cos(np.deg2rad(135)), .7*np.sin(np.deg2rad(135))),
                   xytext=(-.78, .92), fontsize=9.5, color=MUTED, arrowprops={'arrowstyle': '-', 'color': MUTED, 'lw': .8})
    right.annotate('cloud', (1.2, .23), ha='center', fontsize=11, color=RUST)
    right.text(1.2, -.05, 'speed\ndensity\ntemperature', ha='center', va='top', fontsize=8.5, color=RUST, linespacing=1.5)
    right.annotate('', xy=(2.05, .05), xytext=(1.84, .05), arrowprops={'arrowstyle': '-|>', 'color': RUST, 'lw': 1.8})
    right.text(2.08, .23, 'outward', fontsize=9.5, color=RUST, ha='center')
    right.set(xlim=(-.85, 2.35), ylim=(-1.35, 1.4))
    right.set_title('B  Cone model of a CME', loc='left', fontsize=11, weight='bold', pad=15)
    right.text(-.8, -1.30, 'Dashed lines: edges of the cone; w is the half-width.\nThick arc: boundary cells that take the cloud’s values.', fontsize=10, color=MUTED, va='top', linespacing=1.5)
    fig.text(.035, .97, 'The Parker spiral and the cone model', fontsize=14, weight='bold', va='top')
    fig.text(.035, .025, 'Sketches for illustration. Between the cloud and the Sun, the cone holds only ordinary wind.', fontsize=9, color=MUTED)
    save(fig, 'field-and-cme')


def main(source=None):
    if source:
        import_inputs(Path(source))
    OUTPUT.mkdir(parents=True, exist_ok=True); style()
    geometry_record = geometry(); maps = gong_wsa(); field_and_cme()
    files = [file_receipt(path) for directory in [INPUTS, OUTPUT] for path in sorted(directory.iterdir()) if path.is_file()]
    catalogue = []
    import xml.etree.ElementTree as ET
    for name in ['geometry', 'gong-wsa', 'field-and-cme']:
        view = ET.parse(OUTPUT / (name + '.svg')).getroot().attrib['viewBox'].split()
        catalogue.append({'id': name, 'url': '/assets/summary/figures/' + name + '.svg',
                          'width': float(view[2]), 'height': float(view[3]), 'sha256': digest(OUTPUT / (name + '.svg'))})
    (BASE / 'figure-manifest.json').write_text(json.dumps({
        'schemaVersion': 1, 'figures': catalogue, 'files': files, 'geometry': geometry_record, 'magnetogramAndWsa': maps,
        'builder': {'path': 'scripts/build_summary_figures.py', 'sha256': digest(Path(__file__)),
                    'matplotlib': matplotlib.__version__, 'numpy': np.__version__},
        'interpretation': ['Only the geometry and magnetogram/WSA panels use archived measurements or model products.',
                           'The Parker and cone drawings are conceptual illustrations; they do not identify any particular event.',
                           'No research solvers or coronal extrapolations were rerun. The WSA law is evaluated only to verify archived inputs.'],
    }, indent=2, ensure_ascii=False) + '\n')
    print(f'Rendered three static figures; WSA law matches native output to {maps["velocityLawMaximumErrorKms"]:.3g} km/s.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Import original maps and exact ephemeris rows; otherwise use committed figure inputs.')
    main(parser.parse_args().source)
