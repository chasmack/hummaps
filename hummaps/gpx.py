import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom
from datetime import datetime, timedelta
import io, pytz, math, re
import dxfgrabber
import ezdxf

import numpy as np
import numpy.linalg as la
from math import sqrt, hypot, radians, degrees, pi
from math import sin, cos, atan, atan2, asin

from osgeo import ogr, osr

# NAD83 ellipsoid (meters)
A_NAD83 = 6378137.0
F_NAD83 = 1 / 298.257222101
B_NAD834 = A_NAD83 * (1 - F_NAD83)
E2_NAD83 = 2 * F_NAD83 - F_NAD83 ** 2

# WGS84 ellipsoid (meters)
A_WGS84 = 6378137.0
F_WGS84 = 1 / 298.257223563
B_WGS84 = A_WGS84 * (1 - F_WGS84)
E2_WGS84 = 2 * F_WGS84 - F_WGS84 ** 2

SRID_NAD83 = 4269
SRID_WGS84 = 4326

WPT_SYMBOL = 'Flag, Red'


class NonConvergenceError(Exception):
    pass


# Convert geographic coordinates (decimal degrees, meters) to ECEF cartesian coordinates
def geographic_to_cartesian(lon, lat, h, nad83=False):
    lon, lat = map(radians, (lon, lat))

    a, e2 = (A_NAD83, E2_NAD83) if nad83 else (A_WGS84, E2_WGS84)

    N = a / sqrt(1 - e2 * sin(lat) ** 2)
    x = (N + h) * cos(lat) * cos(lon)
    y = (N + h) * cos(lat) * sin(lon)
    z = (N * (1 - e2) + h) * sin(lat)

    return x, y, z


# Convert ECEF cartesian coordinates to geographic coordinates
def cartesian_to_geographic(x, y, z, nad83=False):
    a, e2 = (A_NAD83, E2_NAD83) if nad83 else (A_WGS84, E2_WGS84)

    # Terminate iterative soln when delta is satisfied
    LATITIUE_DELTA = 1E-12
    ITERATION_LIMIT = 10

    lon = atan2(y, x)
    p = hypot(x, y)

    last_lat = 0.0
    i = 0
    while True:
        i += 1

        # Calculate a new latitude from the previous result
        N = a / sqrt(1 - e2 * sin(last_lat) ** 2)
        lat = atan(z / p / (1 - e2 * N * cos(last_lat) / p))

        # Check latitude delta and iteration limit
        if abs(lat - last_lat) < LATITIUE_DELTA:
            break
        if i > ITERATION_LIMIT:
            raise NonConvergenceError()
        last_lat = lat

    h = p / cos(lat) - a / sqrt(1 - e2 * sin(lat) ** 2)

    lon, lat = map(degrees, (lon, lat))
    return lon, lat, h


def nad83_to_wgs84(lon, lat, h, inverse=False):

    # Helmert 7-parameter transformation parameters (coordinate frame rotation)
    # tx (m), ty (m), tz (m), rx (arc-seconds), ry (arc-seconds), rz (arc-seconds), ds (ppm)
    # See ArcGIS Geographic and Vertical Transformation Tables
    # NAD_1983_To_WGS_1984_5 WKID: 1515

    tx, ty, tz, rx, ry, rz, ds = (
        -0.9910, +1.9072, +0.5129,
        -0.02578991 / 3600 / 180 * pi,
        -0.00965010 / 3600 / 180 * pi,
        -0.01165994 / 3600 / 180 * pi,
        +0.0
    )

    # Rotation matrix
    # R = np.array((
    #     + cos(ry) * cos(rz),
    #     + cos(rx) * sin(rz) + sin(rx) * sin(ry) * cos(rz),
    #     + sin(rx) * sin(rz) - cos(rx) * sin(ry) * cos(rz),
    #     - cos(ry) * sin(rz),
    #     + cos(rx) * cos(rz) - sin(rx) * sin(ry) * sin(rz),
    #     + sin(rx) * cos(rz) + cos(rx) * sin(ry) * sin(rz),
    #     + sin(ry),
    #     - sin(rx) * cos(ry),
    #     + cos(rx) * cos(ry)
    # ), dtype=np.double).reshape((3, 3))

    # Approximate rotation matrix for very small rotation angels
    R = np.array((
        (1.0, +rz, -ry),
        (-rz, 1.0, +rx),
        (+ry, -rx, 1.0)
    ), dtype=np.double)

    # Translation vector
    T = np.array((tx, ty, tz), dtype=np.double)

    # Scale factor
    M =  1.0 + ds * 1e-6

    if inverse:
        # WGS84 to NAD83
        R = la.inv(R)
        M = 1.0 / M
        Vs = geographic_to_cartesian(lon, lat, h, nad83=False)
        Vt = M * R.dot(Vs - T)
        lon, lat, h = cartesian_to_geographic(*Vt, nad83=True)
    else:
        # NAD83 to WGS84
        Vs = geographic_to_cartesian(lon, lat, h, nad83=True)
        Vt = M * R.dot(Vs) + T
        lon, lat, h = cartesian_to_geographic(*Vt, nad83=False)

    return lon, lat, h


# Transform points in place from projected coordinates to WGS84 geographic (4326)
def projected_to_wgs84(pnts, srid_source):

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
        if sr_source.GetAttrValue('GEOGCS') == 'NAD83':
            lon, lat, h = nad83_to_wgs84(lon, lat, 0.0, inverse=False)
        p[0:3] = (lon, lat, ele)


# Transform points in place from WGS84 geographic (4326) to projected coordinates
def wgs84_to_projected(pnts, srid_target):
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
        if sr_target.GetAttrValue('GEOGCS') == 'NAD83':
            lon, lat, h = nad83_to_wgs84(lon, lat, 0.0, inverse=True)
        geom = ogr.CreateGeometryFromWkt('POINT (%s %s)' % (lon, lat))
        geom.Transform(source_to_target)
        x, y = geom.GetX(), geom.GetY()
        p[0:3] = (x, y, ele)


def pnts_sort_key(p):
    if p[4] and p[4].isdigit():
        return int(p[4])
    else:
        return -1


def pnezd_out(pnts, srid_target):

    # Transform WGS84 to the target coordinate system
    wgs84_to_projected(pnts, srid_target)

    pnezd = ''
    for p in sorted(pnts, key=pnts_sort_key):
        # x, y, ele, time, name, cmt, desc, sym, type, samples
        x, y, ele = p[0:3]
        name = '%d' % int(p[4]) if p[4] and p[4].isdigit() else ''
        desc = p[5] or p[6] or ''
        pnezd += '%s,%.4f,%.4f,%.4f,%s\n' % (name, y, x, ele, desc)

    return pnezd


def pnezd_in(f, srid_source):

    # Read a pnezd comma delimited points file
    pnts = []
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
        pnts.append([x, y, ele, None, name, None, desc, None, None, None])

    # Transform points to WGS84 lon/lat (4326)
    projected_to_wgs84(pnts, srid_source)

    return pnts


# Parse wpt elements into a list of ordered tuples
def gpx_in(f):

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

    pnts = []
    gpx = etree.parse(f).getroot()
    for wpt in gpx.findall('gpx:wpt', ns):
        pnt = list(map(float, (wpt.get('lon'), wpt.get('lat'))))
        for tag in wpt_elems:
            elem = wpt.find(tag, ns)
            pnt.append(None if elem is None else elem.text)

        # Check the elevation
        pnt[2] = 0.0 if pnt[2] is None else float(pnt[2])
        pnts.append(pnt)

    return pnts


def gpx_out(pnts):
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
    time = time.isoformat()

    gpx = etree.Element('gpx', attrib=gpx_attrib)
    meta = etree.SubElement(gpx, 'metadata')
    link = etree.SubElement(meta, 'link', attrib={'href': 'https://hummaps.org/'})
    etree.SubElement(link, 'text').text = 'Charlie'
    etree.SubElement(meta, 'time').text = time

    for p in sorted(pnts, key=pnts_sort_key):
        # lon, lat, ele, time, name, cmt, desc, sym, type, samples
        lon, lat = ('%.8f' % c for c in p[0:2])
        wpt = etree.SubElement(gpx, 'wpt', attrib={'lat': lat, 'lon': lon})
        etree.SubElement(wpt, 'ele').text = '%.4f' % p[2]

        # Format wpt name
        p[4] = '%04d' % int(p[4]) if p[4] and p[4].isdigit() else p[4]

        # Default wpt symbol
        p[7] = p[7] or WPT_SYMBOL

        for tag, i in zip(('time', 'name', 'cmt', 'desc', 'sym', 'type'), range(3,9)):
            if p[i]:
                etree.SubElement(wpt, tag).text = p[i]

        # gpx:extensions/wptx1:WaypointExtension/wptx1:Samples
        # if p[9]:
        #     ext = etree.SubElement(wpt, 'extensions')
        #     wptx1 = etree.SubElement(ext, 'wptx1:WaypointExtension')
        #     etree.SubElement(wptx1, 'wptx1:Samples').text = p[9]

    # Reparse the etree with minidom and write pretty xml.
    return minidom.parseString(etree.tostring(gpx, encoding='utf-8')).toprettyxml(indent='  ')


if __name__ == '__main__':

    # with open('data/PantherGap190321_Clean.gpx', 'rb') as f:
    #     pnts = gpx_in(f)
    # pnezd = pnezd_out(pnts, 2225)
    # print(pnezd)

    with open('data/NAD_1983_To_WGS_1984_5.txt', 'rb') as f:
        pnts = pnezd_in(f, 2225)
    gpx = gpx_out(pnts)
    print(gpx)

    exit(0)


# def dxf_in(f, srid):
#
#     dxf = dxfgrabber.read(f)
#
#     wkt = {}
#     for ent in dxf.entities:
#
#         layer = ent.layer
#         if layer.startswith('CONTOUR'):
#             continue    # skip contours
#
#         if layer not in wkt:
#             wkt[layer] = []
#
#         if ent.dxftype == 'LINE':
#             wkt[layer].append('LINESTRING (%f %f, %f %f)' % (ent.start[0], ent.start[1], ent.end[0], ent.end[1]))
#
#         elif ent.dxftype == 'ARC':
#
#             # calc the endpoints of the arc
#             c = ent.center
#             r = ent.radius
#             t0 = math.radians(ent.start_angle)
#             t1 = math.radians(ent.end_angle)
#             p0 = (c[0] + r * math.cos(t0), c[1] + r * math.sin(t0))
#             p1 = (c[0] + r * math.cos(t1), c[1] + r * math.sin(t1))
#
#             # calc the midpoint on the arc
#             m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
#             t = math.atan2(m[1] - c[1], m[0] - c[0])
#             pm = (c[0] + r * math.cos(t), c[1] + r * math.sin(t))
#
#             wkt[layer].append('LINESTRING (%f %f, %f %f, %f %f)' % (p0[0], p0[1], pm[0], pm[1], p1[0], p1[1]))
#
#         elif ent.dxftype == 'LWPOLYLINE':
#             verts = []
#             for i in range(len(ent.points) - 1):
#                 p0 = ent.points[i]
#                 verts.append('%f %f' % (p0[0], p0[1]))
#
#                 b = ent.bulge[i]
#                 if b != 0:
#                     # next segment is an arc, add the midpoint
#                     p1 = ent.points[i + 1]
#                     d = math.sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) / 2  # length to midpoint of the chord
#                     t = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) - math.atan(b)  # direction p0 to pm
#                     c = math.sqrt(1 + b**2) * d  # length p0 to pm
#                     pm = (p0[0] + c * math.cos(t), p0[1] + c * math.sin(t))
#                     verts.append('%f %f' % (pm[0], pm[1]))
#
#                     # r = d / math.sin(2 * math.atan(b))  # signed radius
#                     # print('p0=(%.4f,%.4f) p1=(%.4f,%.4f) b=%.8f t=%.4f c=%.4f r=%.4f' % (p0[0],p0[1], p1[0],p1[1], b, math.degrees(t), c, r))
#
#             # add the last vertex and build the wkt
#             p = ent.points[-1]
#             verts.append('%f %f' % (p[0], p[1]))
#             wkt[layer].append('LINESTRING (%s)' % ', '.join(verts))
#
#         else:
#             # print('Skipping dxftype=%s layer=%s' % (ent.dxftype, ent.layer))
#             continue
#
#     # create geometry
#     geom = []
#     for layer in wkt.keys():
#         for i in range(len(wkt[layer])):
#             g = ogr.CreateGeometryFromWkt(wkt[layer][i])
#             geom.append({'name': '%s-%03d' % (layer, i + 1), 'geom': g})
#
#
#     # transform geometry to WGS 84 Lon/Lat (EPSG:4326)
#     source = osr.SpatialReference()
#     source.ImportFromEPSG(srid)
#     wgs84 = osr.SpatialReference()
#     wgs84.ImportFromEPSG(4326)
#
#     transform = osr.CoordinateTransformation(source, wgs84)
#     for rec in geom:
#         rec['geom'].Transform(transform)
#
#     return geom
#
#
# def dxf_out(geom, srid):
#
#     dwg = ezdxf.new('R2004')
#     dwg.layers.new(name='GPX-TRACKS', dxfattribs={'linetype': 'CONTINUOUS', 'color': 7})
#     msp = dwg.modelspace()
#
#     # transform geometry from WGS 84 Lon/Lat (EPSG:4326) to currentMap srs
#     wgs84 = osr.SpatialReference()
#     wgs84.ImportFromEPSG(4326)
#     target = osr.SpatialReference()
#     target.ImportFromEPSG(srid)
#
#     transform = osr.CoordinateTransformation(wgs84, target)
#     for rec in geom:
#         rec['geom'].Transform(transform)
#         if 'ele' in rec:
#             # convert elevation to currentMap linear units
#             rec['ele'] = '%.4f' % (float(rec['ele']) / target.GetLinearUnits())
#
#     for g in [g['geom'] for g in geom]:
#         if g.GetGeometryName() != 'LINESTRING':
#             continue
#         pts = []
#         for i in range(g.GetPointCount()):
#             p = g.GetPoint(i)
#             if p[0] < 0 or p[1] < 0:
#                 pts = []
#                 break
#             pts.append((p[0], p[1]))
#         if pts:
#             msp.add_lwpolyline(pts, dxfattribs={'layer': 'GPX-TRACKS'})
#
#     with io.StringIO() as out:
#         dwg.write(out)
#         dxf = out.getvalue()
#
#     return dxf
#
