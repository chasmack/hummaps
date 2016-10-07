import re
from sqlalchemy import and_, or_

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage

def tshp(t):
    tshp = None
    m = re.search('T(\d{1,2})([NS])', t)
    if m:
        if m.group(2) == 'N':
            tshp = int(m.group(1)) - 1
        else:
            tshp = -1 * int(m.group(1))
    return tshp

def rng(r):
    rng = None
    m = re.search('R*(\d{1,2})([EW])', r)
    if m:
        if m.group(2) == 'E':
            rng = int(m.group(1)) - 1
        else:
            rng = -1 * int(m.group(1))
    return rng


def subsection(ss):

    # bit patterns for first (right) term
    q_bits = {
        'NE': 0x00CC, 'SE': 0xCC00, 'SW': 0x3300, 'NW': 0x0033,
        'N': 0x00FF, 'S': 0xFF00, 'E': 0xCCCC, 'W': 0x3333
    }

    # bit patterns for second (left) term
    qq_bits = {
        'NE': 0x0A0A, 'SE': 0xA0A0, 'SW': 0x5050, 'NW': 0x0505,
        'N': 0x0F0F, 'S': 0xF0F0, 'E': 0xAAAA, 'W': 0x5555
    }

    # xx/4 and xx/4 xx/4
    m = re.fullmatch('(?:([NS][EW])/4\s+)?([NS][EW])/4', ss)
    if m:
        qq, q = m.groups()
        return q_bits[q] if qq is None else q_bits[q] & qq_bits[qq]

    # x/2 and x/2 x/2
    m = re.fullmatch('(?:([NSEW])/2\s+)?([NSEW])/2', ss)
    if m:
        qq, q = m.groups()
        if qq and re.match('E[NS]|[NS]W', ''.join(sorted([q,qq]))):
            # this algorithm doesn't work for N/2 E/2, etc (and it shouldn't have to)
            return None
        return q_bits[q] if qq is None else q_bits[q] & qq_bits[qq]

    # x/2 xx/4
    m = re.fullmatch('([NSEW])/2\s+([NS][EW])/4', ss)
    if m:
        qq, q = m.groups()
        return q_bits[q] & qq_bits[qq]

    return None


def township_range_section(strm):

    # parse off any sections and subsections
    secs = []
    for s in re.findall('((?:(?:[NSEW]+/[24]\s+)?[NSEW]+/[24]\s+)?S\d{1,2}),?\s+', strm):
        m = re.fullmatch('((?:[NSEW]+/[24]\s+)?[NSEW]+/[24])?\s*S(\d+)\s*', s)
        if m:
            if m.group(1) is not None:
                qqsec = subsection(m.group(1))
                if qqsec is None:
                    return 'Subsection error: "%s"' % (s)
            else:
                qqsec = None
            sec = int(m.group(2))
            if sec < 1 or sec > 36:
                return 'Section number error: "$s"' % (s)

            secs.append({'sec': sec, 'qqsec': qqsec})

        else:
            return 'Section formatting error: "%s"' % (s)

    m = re.search('(T\d{1,2}[NS])\s+(R\d{1,2}[EW])\s*$', strm)
    if m:
        t = tshp(m.group(1))
        r = rng(m.group(2))
        trs = {'tshp': t, 'rng': r, 'secs': secs}
    else:
        return 'Township/Range format error: "%s"' % (strm)

    return trs


def do_search(search):

    # split into multiple independent searches terms to be OR'ed together
    search_terms = []
    for term in  re.split('\s*\+\s*', search.upper().strip()):

        # parse and remove maptype, desc, surveyor, client and date
        desc = re.findall('"([^"]+)"', term)
        term = re.sub('\s*"[^"]*"\s*', '', term)

        # township/range/sections should be all that's left
        trs = township_range_section(term) if term != '' else None

        t = []
        if desc:
            t.append(and_( *[ Map.description.op('~')(d) for d in desc] ))

        if trs:
            t.append(and_(TRS.tshp == trs['tshp'], TRS.rng == trs['rng']))
            secs = []
            for sec in trs['secs']:

                if sec['qqsec']:
                    secs.append(and_(TRS.sec == sec['sec'], TRS.qqsec.op('&')(sec['qqsec']) != 0))
                else:
                    secs.append(and_(TRS.sec == sec['sec']))
            if secs:
                t.append(or_(*secs))

        search_terms.append(and_(*t))
        print(search_terms)

    if search_terms:
        query = db_session.query(Map).join(TRS).join(MapType)
        query = query.filter(or_(*search_terms))
        query = query.order_by(MapType.maptype, Map.recdate.desc(), Map.page.desc())
        results = query.all()

    else:
        results = None

    return results

if __name__ == '__main__':

    strm = 's/2 s32 t7n r1e + n/2 s5 t6n r1e'
    print('search: "%s"' % (strm))
    results = do_search(strm)
    n = len(results)

    for i in range(n):

        map = results[i]

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

        print('%2d %6d %s %s' % (i + 1, map.id, map.maptype.abbrev.upper(), map.bookpage))
        # print(map.heading)
        # print(map.line1)
        # print(map.line2)
        # print(map.url())
        # print()


    print('\nresults: %d maps' % (n))

    # cards = ['N', 'S', 'E', 'W']
    # for a in cards:
    #     for b in cards:
    #         s = ''.join(sorted([a,b]))
    #         c = 'NO' if re.match('E[NS]|[NS]W', s) else 'YES'
    #         print(a,b,c)
    #         s = ''.join(sorted([b,a]))
    #         c = 'NO' if re.match('E[NS]|[NS]W', s) else 'YES'
    #         print(b,a,c)


    # ss = ['NE/4', 'SE/4', 'SW/4', 'NW/4', 'N/2', 'S/2', 'E/2', 'W/2']
    # for q in ss:
    #
    #     subsec = q
    #     qq_bits = subsection(subsec)
    #     if qq_bits is not None:
    #         print('assert subsection(\'%s\') == 0x%04X' % (subsec, qq_bits))
    #     else:
    #         print('assert subsection(\'%s\') is None' % (subsec))
    #
    #     for qq in ss:
    #
    #         subsec = qq + ' ' + q
    #         qq_bits = subsection(subsec)
    #         if qq_bits is not None:
    #             print('assert subsection(\'%s\') == 0x%04X' % (subsec, qq_bits))
    #         else:
    #             print('assert subsection(\'%s\') is None' % (subsec))


    assert subsection('NE/4') == 0x00CC
    assert subsection('NE/4 NE/4') == 0x0008
    assert subsection('SE/4 NE/4') == 0x0080
    assert subsection('SW/4 NE/4') == 0x0040
    assert subsection('NW/4 NE/4') == 0x0004
    assert subsection('N/2 NE/4') == 0x000C
    assert subsection('S/2 NE/4') == 0x00C0
    assert subsection('E/2 NE/4') == 0x0088
    assert subsection('W/2 NE/4') == 0x0044
    assert subsection('SE/4') == 0xCC00
    assert subsection('NE/4 SE/4') == 0x0800
    assert subsection('SE/4 SE/4') == 0x8000
    assert subsection('SW/4 SE/4') == 0x4000
    assert subsection('NW/4 SE/4') == 0x0400
    assert subsection('N/2 SE/4') == 0x0C00
    assert subsection('S/2 SE/4') == 0xC000
    assert subsection('E/2 SE/4') == 0x8800
    assert subsection('W/2 SE/4') == 0x4400
    assert subsection('SW/4') == 0x3300
    assert subsection('NE/4 SW/4') == 0x0200
    assert subsection('SE/4 SW/4') == 0x2000
    assert subsection('SW/4 SW/4') == 0x1000
    assert subsection('NW/4 SW/4') == 0x0100
    assert subsection('N/2 SW/4') == 0x0300
    assert subsection('S/2 SW/4') == 0x3000
    assert subsection('E/2 SW/4') == 0x2200
    assert subsection('W/2 SW/4') == 0x1100
    assert subsection('NW/4') == 0x0033
    assert subsection('NE/4 NW/4') == 0x0002
    assert subsection('SE/4 NW/4') == 0x0020
    assert subsection('SW/4 NW/4') == 0x0010
    assert subsection('NW/4 NW/4') == 0x0001
    assert subsection('N/2 NW/4') == 0x0003
    assert subsection('S/2 NW/4') == 0x0030
    assert subsection('E/2 NW/4') == 0x0022
    assert subsection('W/2 NW/4') == 0x0011
    assert subsection('N/2') == 0x00FF
    assert subsection('NE/4 N/2') is None
    assert subsection('SE/4 N/2') is None
    assert subsection('SW/4 N/2') is None
    assert subsection('NW/4 N/2') is None
    assert subsection('N/2 N/2') == 0x000F
    assert subsection('S/2 N/2') == 0x00F0
    assert subsection('E/2 N/2') is None
    assert subsection('W/2 N/2') is None
    assert subsection('S/2') == 0xFF00
    assert subsection('NE/4 S/2') is None
    assert subsection('SE/4 S/2') is None
    assert subsection('SW/4 S/2') is None
    assert subsection('NW/4 S/2') is None
    assert subsection('N/2 S/2') == 0x0F00
    assert subsection('S/2 S/2') == 0xF000
    assert subsection('E/2 S/2') is None
    assert subsection('W/2 S/2') is None
    assert subsection('E/2') == 0xCCCC
    assert subsection('NE/4 E/2') is None
    assert subsection('SE/4 E/2') is None
    assert subsection('SW/4 E/2') is None
    assert subsection('NW/4 E/2') is None
    assert subsection('N/2 E/2') is None
    assert subsection('S/2 E/2') is None
    assert subsection('E/2 E/2') == 0x8888
    assert subsection('W/2 E/2') == 0x4444
    assert subsection('W/2') == 0x3333
    assert subsection('NE/4 W/2') is None
    assert subsection('SE/4 W/2') is None
    assert subsection('SW/4 W/2') is None
    assert subsection('NW/4 W/2') is None
    assert subsection('N/2 W/2') is None
    assert subsection('S/2 W/2') is None
    assert subsection('E/2 W/2') == 0x2222
    assert subsection('W/2 W/2') == 0x1111


