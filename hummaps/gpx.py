import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom
from datetime import datetime, timedelta
import io, pytz, math, re
import dxfgrabber
import ezdxf

from osgeo import ogr, osr


def gpx_read(f):
    """ Parse wpt elements from a GPX file and transform coordinates to grid.
    """

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

    geom = []
    gpx = etree.parse(f).getroot()
    for wpt in gpx.findall('gpx:wpt', ns):
        rec = {}
        rec['geom'] = ogr.CreateGeometryFromWkt('POINT (%s %s)' % (wpt.get('lon'), wpt.get('lat')))
        tags = ['gpx:ele', 'gpx:time', 'gpx:name', 'gpx:cmt', 'gpx:desc', 'gpx:sym', 'gpx:type']
        tags += ['./gpx:extensions//wptx1:Samples']
        for t in tags:
            e = wpt.find(t, ns)
            if e is not None:
                k = t.rpartition(':')[2].lower()  # remove path and namespace
                rec[k] = e.text

        geom.append(rec)

    for trk in gpx.findall('gpx:trk', ns):

        # idle time between trkpts to start a new segment
        TRKSEG_IDLE_SECS = 600

        for trkseg in trk.findall('gpx:trkseg', ns):
            g = ogr.Geometry(ogr.wkbLineString)
            dtlast = None
            for trkpt in trkseg.findall('gpx:trkpt', ns):
                time = trkpt.find('gpx:time', ns)
                if time is not None:
                    if re.match('.*:\d{2}\.\d+Z$', time.text, re.IGNORECASE):
                        # parse with microseconds
                        dt = datetime.strptime(time.text, '%Y-%m-%dT%H:%M:%S.%fZ')
                    else :
                        # parse with only full seconds
                        dt = datetime.strptime(time.text, '%Y-%m-%dT%H:%M:%SZ')
                    if dtlast and (dt - dtlast).seconds > TRKSEG_IDLE_SECS:
                        # start a new segment
                        geom.append({'geom': g})
                        g = ogr.Geometry(ogr.wkbLineString)
                    dtlast = dt
                g.AddPoint_2D(float(trkpt.get('lon')), float(trkpt.get('lat')))
            geom.append({'geom': g})

    return geom


def gpx_out(geom):
    """ Format a list of point/linestring geometry as a GPX file.

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
    link = etree.SubElement(meta, 'link', attrib={'href': 'https://cmack.org/'})
    etree.SubElement(link, 'text').text = 'Charlie'
    etree.SubElement(meta, 'time').text = time

    for rec in geom:
        g = rec['geom']
        type = g.GetGeometryName()
        if type == 'LINESTRING':
            rte = etree.SubElement(gpx, 'rte')
            if 'name' in rec:
                etree.SubElement(rte, 'name').text = rec['name']

            for i in range(g.GetPointCount()):
                p = g.GetPoint(i)
                lon = '%.8f' % p[0]
                lat = '%.8f' % p[1]
                rtept = etree.SubElement(rte, 'rtept', attrib={'lat': lat, 'lon': lon})
                if 'name' in rec:
                    etree.SubElement(rtept, 'name').text = rec['name'] + '.%03d' % (i + 1)
                etree.SubElement(rtept, 'sym').text = 'Waypoint'

        elif type == 'POINT':
            lon = '%.8f' % g.GetX()
            lat = '%.8f' % g.GetY()
            wpt = etree.SubElement(gpx, 'wpt', attrib={'lat': lat, 'lon': lon})

            if 'ele' in rec:
                etree.SubElement(wpt, 'ele').text = '%.4f' % float(rec['ele'])
            if 'name' in rec:
                etree.SubElement(wpt, 'name').text = rec['name']
            if 'cmt' in rec:
                etree.SubElement(wpt, 'cmt').text = rec['cmt']
            if 'desc' in rec:
                etree.SubElement(wpt, 'desc').text = rec['desc']

            etree.SubElement(wpt, 'sym').text = 'Flag, Red'

    # Reparse the etree with minidom and write pretty xml.
    return minidom.parseString(etree.tostring(gpx, encoding='utf-8')).toprettyxml(indent='  ')


def dxf_read(f, srid):

    dxf = dxfgrabber.read(f)

    wkt = {}
    for ent in dxf.entities:

        layer = ent.layer
        if layer.startswith('CONTOUR'):
            continue    # skip contours

        if layer not in wkt:
            wkt[layer] = []

        if ent.dxftype == 'LINE':
            wkt[layer].append('LINESTRING (%f %f, %f %f)' % (ent.start[0], ent.start[1], ent.end[0], ent.end[1]))

        elif ent.dxftype == 'ARC':

            # calc the endpoints of the arc
            c = ent.center
            r = ent.radius
            t0 = math.radians(ent.start_angle)
            t1 = math.radians(ent.end_angle)
            p0 = (c[0] + r * math.cos(t0), c[1] + r * math.sin(t0))
            p1 = (c[0] + r * math.cos(t1), c[1] + r * math.sin(t1))

            # calc the midpoint on the arc
            m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            t = math.atan2(m[1] - c[1], m[0] - c[0])
            pm = (c[0] + r * math.cos(t), c[1] + r * math.sin(t))

            wkt[layer].append('LINESTRING (%f %f, %f %f, %f %f)' % (p0[0], p0[1], pm[0], pm[1], p1[0], p1[1]))

        elif ent.dxftype == 'LWPOLYLINE':
            verts = []
            for i in range(len(ent.points) - 1):
                p0 = ent.points[i]
                verts.append('%f %f' % (p0[0], p0[1]))

                b = ent.bulge[i]
                if b != 0:
                    # next segment is an arc, add the midpoint
                    p1 = ent.points[i + 1]
                    d = math.sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) / 2  # length to midpoint of the chord
                    t = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) - math.atan(b)  # direction p0 to pm
                    c = math.sqrt(1 + b**2) * d  # length p0 to pm
                    pm = (p0[0] + c * math.cos(t), p0[1] + c * math.sin(t))
                    verts.append('%f %f' % (pm[0], pm[1]))

                    # r = d / math.sin(2 * math.atan(b))  # signed radius
                    # print('p0=(%.4f,%.4f) p1=(%.4f,%.4f) b=%.8f t=%.4f c=%.4f r=%.4f' % (p0[0],p0[1], p1[0],p1[1], b, math.degrees(t), c, r))

            # add the last vertex and build the wkt
            p = ent.points[-1]
            verts.append('%f %f' % (p[0], p[1]))
            wkt[layer].append('LINESTRING (%s)' % ', '.join(verts))

        else:
            # print('Skipping dxftype=%s layer=%s' % (ent.dxftype, ent.layer))
            continue

    # create geometry
    geom = []
    for layer in wkt.keys():
        for i in range(len(wkt[layer])):
            g = ogr.CreateGeometryFromWkt(wkt[layer][i])
            geom.append({'name': '%s-%03d' % (layer, i + 1), 'geom': g})


    # transform geometry to WGS 84 Lon/Lat (EPSG:4326)
    source = osr.SpatialReference()
    source.ImportFromEPSG(srid)
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(source, wgs84)
    for rec in geom:
        rec['geom'].Transform(transform)

    return geom


def dxf_out(geom, srid):

    dwg = ezdxf.new('R2004')
    dwg.layers.new(name='GPX-TRACKS', dxfattribs={'linetype': 'CONTINUOUS', 'color': 7})
    msp = dwg.modelspace()

    # transform geometry from WGS 84 Lon/Lat (EPSG:4326) to currentMap srs
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    target = osr.SpatialReference()
    target.ImportFromEPSG(srid)

    transform = osr.CoordinateTransformation(wgs84, target)
    for rec in geom:
        rec['geom'].Transform(transform)
        if 'ele' in rec:
            # convert elevation to currentMap linear units
            rec['ele'] = '%.4f' % (float(rec['ele']) / target.GetLinearUnits())

    for g in [g['geom'] for g in geom]:
        if g.GetGeometryName() != 'LINESTRING':
            continue
        pts = []
        for i in range(g.GetPointCount()):
            p = g.GetPoint(i)
            if p[0] < 0 or p[1] < 0:
                pts = []
                break
            pts.append((p[0], p[1]))
        if pts:
            msp.add_lwpolyline(pts, dxfattribs={'layer': 'GPX-TRACKS'})

    with io.StringIO() as out:
        dwg.write(out)
        dxf = out.getvalue()

    return dxf


def pnts_read(f, srid):

    # read a pnezd comma delimited points file
    geom = []
    for bytes in f:

        line = bytes.decode('utf-8').strip()
        if len(line) == 0 or line[0] == '#':
            continue
        values = re.split(',', line, 4)
        if len(values) != 5:
            # print('PNEZD format error: "%s"' % line)
            continue
        p, n, e, z, d = values
        if p.isdigit():
            p = '%03d' % int(p)  # zero pad
        g = ogr.CreateGeometryFromWkt('POINT (%s %s)' % (e, n))
        geom.append({'ele': z, 'name': p, 'cmt': d, 'desc': d, 'geom': g})


    # transform geometry to WGS 84 Lon/Lat (EPSG:4326)
    source = osr.SpatialReference()
    source.ImportFromEPSG(srid)
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)

    transform = osr.CoordinateTransformation(source, wgs84)
    for rec in geom:
        rec['geom'].Transform(transform)
        if 'ele' in rec:
            # convert elevation to meters
            rec['ele'] = '%.4f' % (float(rec['ele']) * source.GetLinearUnits())

    return geom


def pnts_out(geom, srid):

    # transform geometry from WGS 84 Lon/Lat (EPSG:4326) to currentMap srs
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    target = osr.SpatialReference()
    target.ImportFromEPSG(srid)

    transform = osr.CoordinateTransformation(wgs84, target)
    for rec in geom:
        rec['geom'].Transform(transform)
        if 'ele' in rec:
            # convert elevation to currentMap linear units
            rec['ele'] = '%.4f' % (float(rec['ele']) / target.GetLinearUnits())

    pnezd = ''
    p = 0
    for rec in geom:
        g = rec['geom']
        if g.GetGeometryName() != 'POINT':
            continue
        n = '%.4f' % g.GetY()
        e = '%.4f' % g.GetX()
        if 'name' in rec and rec['name'].isdigit():
            p = '%d' % int(rec['name'])
        else:
            p = ''
        if 'ele' in rec:
            z = '%.4f' % float(rec['ele'])
        else:
            z = '0.0000'
        if 'cmt' in rec:
            d = rec['cmt']
        elif 'desc' in rec:
            d = rec['desc']
        else:
            d = ''
        pnezd += (','.join([p,n,e,z,d]) + '\n')

    return pnezd


if __name__ == '__main__':

    with open('data/gpxmap.txt', 'rb') as f:
        geom = pnts_read(f, 2225)

    gpx = gpx_out(geom)
    print(gpx)

    exit(0)

    for rec in geom:
        for k in sorted(rec.keys()):
            if k == 'geom':
                print('%s: %s' % ('geom', rec['geom'].ExportToWkt()))
            else:
                print('%s: %s' % (k, rec[k]))

    print('count: %d' % len(geom))

