import re

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage

def township(t):
    tshp = None
    m = re.search('T\D*(\d{1,2})[^\dNS]*([NS])', t.upper())
    if m:
        if m.group(2) == 'N':
            tshp = int(m.group(1)) - 1
        else:
            tshp = -1 * int(m.group(1))
    return tshp

def range(r):
    rng = None
    m = re.search('R\D*(\d{1,2})[^\dEW]*([EW])', r.upper())
    if m:
        if m.group(2) == 'E':
            rng = int(m.group(1)) - 1
        else:
            rng = -1 * int(m.group(1))
    return rng


def township_range_section(desc):

    # first group picks out the sections
    pat = '((?:S(?:EC|ECTION)?\s*\d{1,2}\s+)+)'

    # second group picks out township/range
    pat += '(T\D*\d{1,2}\s*(?:N|NORTH|S|SOUTH)\s+\R\D*\d{1,2}\s*(?:E|EAST|W|WEST))'

    trs = None
    m = re.search(pat, desc.upper())
    if m:
        tshp = township(m.group(2))
        rng = range(m.group(2))
        secs = [int(s) for s in re.findall('S\D*(\d+)', m.group(1))]
        trs = {'tshp': tshp, 'rng': rng, 'secs': secs}
    return trs


def do_search(desc):

    # parse off the literal search patterns
    literals = re.findall('"([^"]+)"', desc)
    desc = re.sub('\s*"[^"]*"\s*', '', desc)

    # parse off the township/range/sections
    trs = township_range_section(desc)

    query = db_session.query(Map).join(TRS).join(MapType)
    if trs:
        query = query.filter(TRS.tshp == trs['tshp'], TRS.rng == trs['rng'], TRS.sec.in_(trs['secs']))
    for pat in literals:
        query = query.filter(Map.description.op('~')(pat.upper()))
    # query = query.filter(TRS.qqsec.op('&')(1) != 0)
    query = query.order_by(MapType.abbrev, Map.recdate.desc(), Map.page.desc())

    maps = query.all()

    return maps

if __name__ == '__main__':

    results = do_search('s32 t7n r1e "nw/4 s32"')

    for map in results:

        mapimages = ', '.join([mapimage.imagefile for mapimage in map.mapimage])
        if mapimages == '':
            mapimages = 'None'

        certs = []
        for cc in map.cc:
            imagefiles = ', '.join([ccimage.imagefile for ccimage in cc.ccimage])
            if imagefiles == '':
                imagefiles = 'None'
            certs.append('CC=%s (%s)' % (cc.doc_number, imagefiles))
        certs = ', '.join(certs)

        print('%06d: %s (%s) %s' % (map.id, map.bookpage, mapimages, certs))
        print(map.header)
        print(map.line1)
        print(map.line2)
        print(map.url())
        print()

    print('%d maps found.' % (len(results)))


