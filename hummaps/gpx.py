import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom
from datetime import datetime, timedelta
from os import path
import pytz

import numpy as np
# import numpy.linalg as la
from math import sqrt, hypot, radians, degrees, pi
from math import sin, cos, atan, atan2, floor

from osgeo import ogr, osr

# NAD83 ellipsoid (meters)
A_GRS80 = 6378137.0
F_GRS80 = 1 / 298.257222101
B_GRS80 = A_GRS80 * (1 - F_GRS80)
E2_GRS80 = 2 * F_GRS80 - F_GRS80 ** 2

# WGS84 ellipsoid (meters)
A_WGS84 = 6378137.0
F_WGS84 = 1 / 298.257223563
B_WGS84 = A_WGS84 * (1 - F_WGS84)
E2_WGS84 = 2 * F_WGS84 - F_WGS84 ** 2

SRID_NAD83 = 4269
SRID_WGS84 = 4326

WPT_SYMBOL = 'Flag, Red'

#
# Transform ITRF08 to NAD83 in the current epoch then add HTDP displacement.
# This requires a displacement grid in NAD83. The displacement grid is created
# from an NGS HTDP displacement file. The HTDP dispmacement file is large and
# should be generated locally with the PC version of HTDP. The HTDP displacement
# file format-
#
#  HTDP (VERSION v3.2.7    ) OUTPUT
#
#  DISPLACEMENTS IN METERS RELATIVE TO NAD_83(2011/CORS96/2007)
#  FROM 07-02-2019 TO 01-01-2010 (month-day-year)
#  FROM 2019.500 TO 2010.000 (decimal years)
#
# NAME OF SITE             LATITUDE          LONGITUDE            NORTH    EAST    UP
# 2019.50      0   0       38 30  0.00000 N  120  0  0.00000 W   -0.087   0.067   0.013
# 2019.50      0   1       38 30  0.00000 N  120  0 15.00000 W   -0.087   0.067   0.013
# 2019.50      0   2       38 30  0.00000 N  120  0 30.00000 W   -0.087   0.067   0.013
# 2019.50      0   3       38 30  0.00000 N  120  0 45.00000 W   -0.087   0.067   0.013
# 2019.50      0   4       38 30  0.00000 N  120  1  0.00000 W   -0.087   0.067   0.013
# 2019.50      0   5       38 30  0.00000 N  120  1 15.00000 W   -0.087   0.067   0.013
#
# The NORTH and EAST displacements are saved as signed 32-bit integer offsets in mm.
# The columns are arranged such that displacements are accessed as-
#
# e, n = disp_grid[offset_lon, offset_lat]
#
# A dims file is saved with the grid file defining the base lon/lat and step size.
# For the HTDP displacement file shown above the dims are-
#
# base_lon = -120.00000000 (negative west)
# base_lat = 38.300000000
# step_lon = 15 (arc-seconds)
# step_lat = 15
#
# At this time the current epoch is taken to be 2019.50. In future a velocity grid
# could calculate small differences between 2019.50 and the actual epoch of the point.


HTDP_DISP_FILE = 'data/disp-grid-nad83-2019.50.txt'
HTDP_SITE_NAME = '2019.50'

DISP_GRID_FILE = 'data/disp-grid-nad83-2019.50.npy'
DISP_DIMS_FILE = 'data/disp-grid-nad83-2019.50.dim'


def make_disp_grid(htdp_file, grid_file, dims_file, site):

    grid = []
    row = []
    with open(htdp_file, 'r') as f:

        # Get the base lon/lat and step size in arc-seconds
        base_lon = base_lat = None
        step_lon = step_lat = None
        for line in f:
            if line.startswith(site):

                # Parse indices positionally, split remaining fields
                i = int(line[10:14].strip())
                j = int(line[14:18].strip())
                fields = line[18:].split()

                if i == 0 and j == 0:
                    d, m, s = map(float, fields[0:3])
                    base_lat = d + m / 60 + s / 3600
                    d, m, s = map(float, fields[4:7])
                    base_lon = -1 * (d + m / 60 + s / 3600)
                elif i == 0 and j == 1:
                    d, m, s = map(float, fields[4:7])
                    step_lon = round(((d + m / 60 + s / 3600) + base_lon) * 3600)
                elif i == 1 and j == 0:
                    d, m, s = map(float, fields[0:3])
                    step_lat = round(((d + m / 60 + s / 3600) - base_lat) * 3600)
                    break

        f.seek(0)
        for line in f:
            if line.startswith(site):
                fields = line.split()
                i, j = map(int, fields[1:3])
                if j == 0 and row:
                    grid.append(row)
                    row = []
                n, e = map(lambda n: int(float(n) * 1000), fields[-3:-1])
                row.append((e,n))
        if row:
            grid.append(row)

        # Grid of signed integers representing mm displacements accessed as grid(lon, lat)
        grid = np.array(grid, dtype=np.int32).swapaxes(0, 1)
        np.save(grid_file, grid)

        # Dimensions file
        with open(dims_file, 'w') as f:
            f.write('%f %f %d %d' % (base_lon, base_lat, step_lon, step_lat))


    return




# Load the displacement grid
def load_disp_grid(grid_file, dims_file):
    grid = np.load(grid_file)
    with open(dims_file, 'r') as f:
        fields =  f.read().split()
        base_lon, base_lat = map(float, fields[0:2])
        step_lon, step_lat = map(int, fields[2:4])

    return grid, (base_lon, base_lat, step_lon, step_lat)


# Get a displacement from the grid
def get_disp(P, grid, grid_dims):
    lon, lat, h = P

    # Get the nearest displacement
    dim_i, dim_j = grid.shape[0:2]
    base_lon, base_lat, step_lon, step_lat = grid_dims
    i = (lon - base_lon) * 3600 / step_lon * -1
    j = (lat - base_lat) * 3600 / step_lat
    mod_lon = i % 1
    mod_lat = j % 1
    i = floor(i)
    j = floor(j)

    if i < 0 or i + 1 >= dim_i or j < 0 or j + 1 >= dim_j:
        return None

    LR = grid[i,j].astype(np.float)
    LL = grid[i+1,j].astype(np.float)
    UR = grid[i,j+1].astype(np.float)
    UL = grid[i+1,j+1].astype(np.float)

    D = (1 - mod_lat) * ((1 - mod_lon) * LR + mod_lon * LL)
    D += mod_lat * ((1 - mod_lon) * UR + mod_lon * UL)
    D /= 1000

    e, n = D.flat
    u = 0.0

    return (e, n, u)


# Add a northing/easting/up displacement to point
def add_enu_disp(P, D):
    lon, lat, h = P

    # Rotation matrix from ECEF to ENU by Misra/Enge page 137
    #
    # R = R1(-lon + 90) * R3(lat + 90)
    # Vd = R * (V1 - V0)
    #
    # Since R is orthogonal
    #
    # inv(R) = R.T
    # V1 = R.T * Vd + V0
    #

    V0 = np.array(ellip_to_cart(P))
    Vd = np.array(D)

    sl, sp = map(lambda d: sin(radians(d)), (lon, lat))
    cl, cp = map(lambda d: cos(radians(d)), (lon, lat))

    R = np.array((
        -sl,    -sp * cl,   +cp * cl,
        +cl,    -sp * sl,   +cp * sl,
        0.0,    +cp,        +sp
    )).reshape((3, 3))
    V1 = R.dot(Vd) + V0

    lon, lat, h = cart_to_ellip(V1)

    return (lon, lat, h)


def itrf_to_nad(P, grid, grid_dims, epoch=2019.50, inverse=False):

    # Helmert 7-parameter transform (coordinate frame rotation)
    # translations - tx, ty, tz (m)
    # rotations - rx, ry, rz (milli-arc-seconds)
    # scale difference - s (ppb)
    #
    # Rates of change per year and reference epoch
    # translations - dtx, dty, dtz (m/year)
    # rotations - drx, dry, drz (milli-arc-seconds/year)
    # scale difference - ds (ppb/year)
    # reference epoch - t0 (decimal year)
    #
    # See EPSG Guidance Note 373-7-2 - Coordinate Conversions and Transformations including Formulas
    #
    # Derived from -
    # ITRF 1997 -> ITRF 2008 (EPSG::6299) by IERS
    # ITRF 1997 -> NAD83(CORS96) (EPSG::6865) by IOGP

    ITRF08_NAD83_2010 = (
        +1.00380,
        -1.91110,
        -0.54350,
        +26.78600,
        -0.41500,
        +11.45600,
        +0.42000,
        +0.00010,
        -0.00050,
        -0.00320,
        +0.05320,
        -0.74230,
        -0.01160,
        +0.09000,
         2010.00
    )
    tx, ty, tz, rx, ry, rz, s = ITRF08_NAD83_2010[0:7]

    if epoch:
        dtx, dty, dtz, drx, dry, drz, ds, t0 = ITRF08_NAD83_2010[7:]
        tx += dtx * (epoch - t0)
        ty += dty * (epoch - t0)
        tz += dtz * (epoch - t0)
        rx += drx * (epoch - t0)
        ry += dry * (epoch - t0)
        rz += drz * (epoch - t0)
        s += ds * (epoch - t0)

    # Convert milli-arc-seconds to radians
    rx, ry, rz = map(lambda n: radians(n / 3.6E+06), (rx, ry, rz))

    # Convert ppd to decimal
    s /= 1.0E+06

    # Rotation matrix for very small rotation angels
    R = np.array((
        (1.0, +rz, -ry),
        (-rz, 1.0, +rx),
        (+ry, -rx, 1.0)
    ), dtype=np.double)

    # Translation vector
    T = np.array((tx, ty, tz), dtype=np.double)

    # Scale factor
    M = 1.0 + s

    # HTDP displacement ITRF08 to NAD83 2010.00
    D = get_disp(P, grid, grid_dims)
    if D is None:
        # Outside displacement grid
        return None
    D = np.array(D)

    if inverse:
        # NAD83 2010.00 -> NAD83 2019.50 (HTDP) -> ITRF08 2019.50
        R = R.T
        M = 1.0 / M
        P = add_enu_disp(P, -D)
        Vs = ellip_to_cart(P, grs80=True)
        Vt = M * R.dot(Vs - T)
        lon, lat, h = cart_to_ellip(Vt, grs80=False)

    else:
        # ITRF08 2019.50 -> NAD83 2019.50 -> NAD83 2010.00 (HTDP)
        Vs = ellip_to_cart(P, grs80=False)
        Vt = M * R.dot(Vs) + T
        P = cart_to_ellip(Vt, grs80=True)
        lon, lat, h = add_enu_disp(P, D)

    return lon, lat, h


# Convert geographic coordinates (decimal degrees, meters) to ECEF cartesian coordinates
def ellip_to_cart(P, grs80=False):
    lon, lat, h = P
    lon, lat = map(radians, (lon, lat))
    a, e2 = (A_GRS80, E2_GRS80) if grs80 else (A_WGS84, E2_WGS84)

    n = a / sqrt(1 - e2 * sin(lat) ** 2)
    x = (n + h) * cos(lat) * cos(lon)
    y = (n + h) * cos(lat) * sin(lon)
    z = (n * (1 - e2) + h) * sin(lat)

    return (x, y, z)


class NonConvergenceError(Exception):
    pass


# Convert ECEF cartesian coordinates to geographic coordinates
def cart_to_ellip(V, grs80=False):
    x, y, z = V
    a, e2 = (A_GRS80, E2_GRS80) if grs80 else (A_WGS84, E2_WGS84)
    lon = atan2(y, x)
    p = hypot(x, y)

    latitiue_delta = 1.0E-12
    iteration_limit = 10
    last_lat = 0.0
    i = 0
    while True:
        i += 1

        # Calculate a new latitude from the previous result
        n = a / sqrt(1 - e2 * sin(last_lat) ** 2)
        lat = atan(z / p / (1 - e2 * n * cos(last_lat) / p))

        # Check latitude delta and iteration limit
        if abs(lat - last_lat) < latitiue_delta:
            break
        if i > iteration_limit:
            raise NonConvergenceError()
        last_lat = lat

    h = p / cos(lat) - a / sqrt(1 - e2 * sin(lat) ** 2)
    lon, lat = map(degrees, (lon, lat))

    return (lon, lat, h)


# Transform points in place from projected coordinates to WGS84 geographic (4326)
def grid_to_ellip(pnts, srid_source):

    # Source spacial reference system
    sr_source = osr.SpatialReference()
    sr_source.ImportFromEPSG(srid_source)

    # Target spatial reference system and coordinate transform
    sr_target = osr.SpatialReference()
    if sr_source.GetAttrValue('GEOGCS') == 'NAD83':
        sr_target.ImportFromEPSG(SRID_NAD83)
    elif sr_source.GetAttrValue('GEOGCS') == 'WGS_1984':
        sr_target.ImportFromEPSG(SRID_WGS84)
    else:
        raise ValueError('Unsupported source datum: SRID=%d' % srid_source)
    source_to_target = osr.CoordinateTransformation(sr_source, sr_target)

    # Transform points to geographic coordinates, elevations to meters
    for p in pnts:
        x, y, ele = p[0:3]
        ele *= sr_source.GetLinearUnits()
        geom = ogr.CreateGeometryFromWkt('POINT (%s %s)' % (x, y))
        geom.Transform(source_to_target)
        lon, lat = geom.GetX(), geom.GetY()
        # if sr_source.GetAttrValue('GEOGCS') == 'NAD83':
        #     lon, lat, h = itrf_to_nad(lon, lat, 0.0, inverse=True, epoch=epoch)
        p[0:3] = (lon, lat, ele)


# Transform points in place from WGS84 geographic (4326) to projected coordinates
def ellip_to_grid(pnts, srid_target):
    # Target spacial reference system
    sr_target = osr.SpatialReference()
    sr_target.ImportFromEPSG(srid_target)

    # Source spatial reference system and coordinate transform
    sr_source = osr.SpatialReference()
    if sr_target.GetAttrValue('GEOGCS') == 'NAD83':
        sr_source.ImportFromEPSG(SRID_NAD83)
    elif sr_target.GetAttrValue('GEOGCS') == 'WGS_1984':
        sr_source.ImportFromEPSG(SRID_WGS84)
    else:
        raise ValueError('Unsupported target datum: SRID=%d' % srid_target)
    source_to_target = osr.CoordinateTransformation(sr_source, sr_target)

    # Transform points to projected coordinates, elevations to target units
    for p in pnts:
        lon, lat, ele = p[0:3]
        ele /= sr_target.GetLinearUnits()
        # if sr_target.GetAttrValue('GEOGCS') == 'NAD83':
        #     lon, lat, h = itrf_to_nad(lon, lat, 0.0, inverse=False, epoch=epoch)
        geom = ogr.CreateGeometryFromWkt('POINT (%s %s)' % (lon, lat))
        geom.Transform(source_to_target)
        x, y = geom.GetX(), geom.GetY()
        p[0:3] = (x, y, ele)


def pnts_sort_key(p):
    if p[4] and p[4].isdigit():
        return int(p[4])
    else:
        return -1


def pnezd_out(pts, srid_target):

    # Transform WGS84 to the target coordinate system
    ellip_to_grid(pts, srid_target)

    pnezd = ''
    for p in sorted(pts, key=pnts_sort_key):
        # x, y, ele, time, name, cmt, desc, sym, type, samples
        x, y, ele = p[0:3]
        name = '%d' % int(p[4]) if p[4] and p[4].isdigit() else ''
        desc = p[5] or p[6] or ''
        pnezd += '%s,%.4f,%.4f,%.4f,%s\n' % (name, y, x, ele, desc)

    return pnezd


def pnezd_in(f, srid_source):

    # Read a pnezd comma delimited points file
    pts = []
    for bytes in f:

        row = bytes.decode('utf-8').strip()
        if len(row) == 0 or row[0] == '#':
            continue
        row = row.split(',', 4)
        if len(row) != 5:
            continue
        name, y, x, ele, desc = row
        x, y, ele = map(float, [x, y, ele])

        # lon, lat, ele, time, name, cmt, desc, sym, type, samples
        pts.append([x, y, ele, None, name, None, desc, None, None, None])

    # Transform points to WGS84 lon/lat (4326)
    grid_to_ellip(pts, srid_source)

    return pts


# Parse wpt elements into a list of ordered tuples
def gpx_in(f, nad83=False):

    ns = {
        'gpx': 'http://www.topografix.com/GPX/1/1',
        'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
        'wptx1': 'http://www.garmin.com/xmlschemas/WaypointExtension/v1',
        'ctx': 'http://www.garmin.com/xmlschemas/CreationTimeExtension/v1',
    }

    etree.register_namespace('', 'http://www.topografix.com/GPX/1/1')
    etree.register_namespace('gpxx', 'http://www.garmin.com/xmlschemas/GpxExtensions/v3')
    etree.register_namespace('wptx1', 'http://www.garmin.com/xmlschemas/WaypointExtension/v1')
    etree.register_namespace('ctx', 'http://www.garmin.com/xmlschemas/CreationTimeExtension/v1')

    wpt_keys = (
        'lon', 'lat', 'ele', 'time', 'name', 'cmt', 'desc', 'sym', 'type', 'samples'
    )
    wpt_elems = (
        'gpx:ele', 'gpx:time', 'gpx:name', 'gpx:cmt',
        'gpx:desc', 'gpx:sym', 'gpx:type', './gpx:extensions//wptx1:Samples'
    )

    pts = []
    gpx = etree.parse(f).getroot()
    for wpt in gpx.findall('gpx:wpt', ns):
        pnt = list(map(float, (wpt.get('lon'), wpt.get('lat'))))
        for tag in wpt_elems:
            elem = wpt.find(tag, ns)
            pnt.append(None if elem is None else elem.text)

        # Check the elevation
        pnt[2] = 0.0 if pnt[2] is None else float(pnt[2])
        pts.append(pnt)

    if nad83:
        grid_file = path.join(path.dirname(__file__), DISP_GRID_FILE)
        dims_file = path.join(path.dirname(__file__), DISP_DIMS_FILE)
        grid, grid_dims = load_disp_grid(grid_file, dims_file)

        i = len(pts)
        while i > 0:
            i -= 1
            lon, lat = pts[i][0:2]
            P = itrf_to_nad((lon, lat, 0.0), grid, grid_dims, inverse=False)
            if P is None:
                # Outside displacement grid - should warn user here
                pts.pop(i)
            else:
                pts[i][0:2] = P[0:2]

    return pts


def gpx_out(pts, nad83=False):
    """ Format a list of points as a GPX file.

    GPX format for waypoints and routes -

    <?xml version="1.0" encoding="utf-8" standalone="no"?>
    <gpx creator="Python pyloc" version="1.1"
        xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd
        xmlns="http://www.topografix.com/GPX/1/1"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" >
        <metadata>
            <link href="http://www.asis.com/users/chas.mack">
                <text>Charles Mack</text>
            </link>
            <time>2015-04-27T23:09:11Z</time>
        </metadata>
        <wpt lat="41.097316" lon="-123.696170">
            <ele>107.753052</ele>
            <time>2015-04-27T23:33:44Z</time>
            <name>4501</name>
            <cmt>SW212</cmt>
            <desc>SW212</desc>
            <sym>Waypoint</sym>
        </wpt>
        <rte>
            <name>ROAD-01</name>
            <rtept lat="41.097316" lon="-123.696170">
                <name>ROAD-01-001</name>
            </rtept>
            <rtept lat="41.123456" lon="-123.789012">
                <name>ROAD-01-002</name>
            </rtept>
        </rte>
    </gpx>

    """

    ns = {
        'gpx': 'http://www.topografix.com/GPX/1/1'
    }
    etree.register_namespace('', 'http://www.topografix.com/GPX/1/1')

    gpx_attrib = {
        'creator': 'hummaps.com/gpx', 'version': '1.1',
        'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd',
        'xmlns': 'http://www.topografix.com/GPX/1/1',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    # Get the ISO 8601 date-time string.
    time = datetime.now(pytz.utc)
    time -= timedelta(microseconds=time.microsecond)  # remove the microseconds
    isotime = time.isoformat()

    gpx = etree.Element('gpx', attrib=gpx_attrib)
    meta = etree.SubElement(gpx, 'metadata')
    link = etree.SubElement(meta, 'link', attrib={'href': 'https://hummaps.org/'})
    etree.SubElement(link, 'text').text = 'Charlie'
    etree.SubElement(meta, 'time').text = isotime

    if nad83:
        grid_file = path.join(path.dirname(__file__), DISP_GRID_FILE)
        dims_file = path.join(path.dirname(__file__), DISP_DIMS_FILE)
        grid, grid_dims = load_disp_grid(grid_file, dims_file)

        i = len(pts)
        while i > 0:
            i -= 1
            lon, lat = pts[i][0:2]
            P = itrf_to_nad((lon, lat, 0.0), grid, grid_dims, inverse=True)
            if P is None:
                # Outside displacement grid - should warn user here
                pts.pop(i)
            else:
                pts[i][0:2] = P[0:2]

    for pt in sorted(pts, key=pnts_sort_key):
        # lon, lat, ele, time, name, cmt, desc, sym, type, samples
        lon, lat = ('%.8f' % c for c in pt[0:2])
        wpt = etree.SubElement(gpx, 'wpt', attrib={'lat': lat, 'lon': lon})
        etree.SubElement(wpt, 'ele').text = '%.4f' % pt[2]

        # Default wpt time
        if pt[3] is None:
            pt[3] = isotime

        # Format wpt name
        pt[4] = '%04d' % int(pt[4]) if pt[4] and pt[4].isdigit() else pt[4]

        # Default wpt symbol
        pt[7] = pt[7] or WPT_SYMBOL

        for tag, i in zip(('time', 'name', 'cmt', 'desc', 'sym', 'type'), range(3,9)):
            if pt[i]:
                etree.SubElement(wpt, tag).text = pt[i]

        # gpx:extensions/wptx1:WaypointExtension/wptx1:Samples
        # if p[9]:
        #     ext = etree.SubElement(wpt, 'extensions')
        #     wptx1 = etree.SubElement(ext, 'wptx1:WaypointExtension')
        #     etree.SubElement(wptx1, 'wptx1:Samples').text = p[9]

    # Reparse the etree with minidom and write pretty xml.
    return minidom.parseString(etree.tostring(gpx, encoding='utf-8')).toprettyxml(indent='  ')


if __name__ == '__main__':

    # TEST_GPX = 'data/grid-limits.gpx'
    # TEST_PNEZD = 'data/grid-limits.txt'
    #
    # with open(TEST_GPX, 'rb') as f:
    #     pnts = gpx_in(f, nad83=True)
    # pnezd = pnezd_out(pnts, 2225)
    # with open(TEST_PNEZD, 'w') as f:
    #     f.write(pnezd)
    # print(pnezd)
    #
    # with open(TEST_PNEZD, 'rb') as f:
    #     pnts = pnezd_in(f, 2225)
    # gpx = gpx_out(pnts, nad83=True)
    # print(gpx)
    #
    # exit(0)

    # make_disp_grid(HTDP_DISP_FILE, DISP_GRID_FILE, DISP_DIMS_FILE, HTDP_SITE_NAME)
    #
    grid, grid_dims = load_disp_grid(DISP_GRID_FILE, DISP_DIMS_FILE)
    #
    # P = (-124.0566589683, 40.2698929701, 0.0)
    # print('   %.10f  %.10f' % (P[0], P[1]))
    #
    # P = itrf_to_nad(P, grid, grid_dims, inverse=False)
    # print('   %.10f  %.10f' % (P[0], P[1]))
    #
    # P = itrf_to_nad(P, grid, grid_dims, inverse=True)
    # print('   %.10f  %.10f' % (P[0], P[1]))
    #
    # exit(0)

    disp = sqrt(np.sum(np.square(grid[0, 0].astype(np.float) / 1000))) * 3937 / 1200
    disp_min = disp_max = disp
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            disp = sqrt(np.sum(np.square(grid[i, j].astype(np.float) / 1000))) * 3937 / 1200
            if disp < disp_min:
                disp_min = disp
            elif disp > disp_max:
                disp_max = disp

    print('min: %.3f ft' % disp_min)  # min: 0.133 ft
    print('max: %.3f ft' % disp_max)  # max: 1.485 ft

