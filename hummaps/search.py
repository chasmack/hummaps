import re
from datetime import date
import calendar
from sqlalchemy import and_, or_

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage

def tshp_num(t):
    tshp = None
    m = re.search('T(\d{1,2})([NS])', t)
    if m:
        if m.group(2) == 'N':
            tshp = int(m.group(1)) - 1
        else:
            tshp = -1 * int(m.group(1))
    return tshp

def rng_num(r):
    rng = None
    m = re.search('R*(\d{1,2})([EW])', r)
    if m:
        if m.group(2) == 'E':
            rng = int(m.group(1)) - 1
        else:
            rng = -1 * int(m.group(1))
    return rng


def subsec_bits(ss):

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
                subsec = subsec_bits(m.group(1))
                if subsec is None:
                    # return 'Subsection error: "%s"' % (s)
                    return None
            else:
                subsec = None
            sec = int(m.group(2))
            if sec < 1 or sec > 36:
                # return 'Section number error: "$s"' % (s)
                return None

            secs.append({'sec': sec, 'subsec': subsec})

        else:
            # return 'Section formatting error: "%s"' % (s)
            return None

    m = re.search('(T\d{1,2}[NS])\s+(R\d{1,2}[EW])\s*$', strm)
    if m:
        t = tshp_num(m.group(1))
        r = rng_num(m.group(2))
        trs = {'tshp': t, 'rng': r, 'secs': secs}
    else:
        # return 'Township/Range format error: "%s"' % (strm)
        return None

    return trs


def parse_dates(d):

    # Parse a date field into a date range.
    # Date fields can be -
    #   "2001" - all maps from 1/1/2001 to 12/31/2001
    #   "6/2001" = all maps from 6/1/2001 to 6/30/2001
    #   "6/15/2001" - all maps from 6/15/2001
    #   "2001 2008" - all maps from 1/1/2001 through 12/31/2008
    #   "6/2001 8/2001" - all maps from 6/1/2001 through 8/31/2001
    #   "6/16/2001 6/30/2001"  - all maps from 6/16/2001 to 6/30/2001

    # a match returns 6 elements ('m1/', 'd1/', 'y1', 'm2/', 'd2/', 'y2')
    # all elements except y1 are optional
    m = re.fullmatch('(?:(\d+/)(\d+/)?)?(\d{4})(?:\s+(?:(\d+/)(\d+/)?)?(\d{4}))?', d.strip())
    if m is None:
        return None

    m1, d1, y1, m2, d2, y2 = m.groups()

    y1 = int(y1)
    if d1:
        m1, d1 = [int(s[0:-1]) for s in (m1, d1)]
        start_date = date(y1, m1, d1)
    elif m1:
        m1 = int(m1[0:-1])
        start_date = date(y1, m1, 1)
    else:
        start_date = date(y1, 1, 1)

    if y2:
        # second date term is present
        y2 = int(y2)
        if d2:
            m2, d2 = [int(s[0:-1]) for s in (m2, d2)]
            end_date = date(y2, m2, d2)
        elif m2:
            m2 = int(m2[0:-1])
            # last day of the month
            end_date = date(y2, m2, calendar.monthrange(y2, m2)[1])
        else:
            # last day of the year
            end_date = date(y2, 12, 31)
    else:
        # second date term missing
        if d1:
            # full date given in first term
            end_date = start_date
        elif m1:
            # search entire month
            end_date = date(y1, m1, calendar.monthrange(y1, m1)[1])
        else:
            # search entire year
            end_date = date(y1, 12, 31)

    return (start_date.isoformat(), end_date.isoformat())


def do_search(search):

    search = search.upper().strip()

    # accumulate terms to be OR'ed together
    search_terms = []

    # first scan query string for maps
    maps = re.findall('\b?(\d+)(CR|HM|MM|PM|RM|RS|UR)(\d+)\b?', search)
    search = re.sub('\s*\d+(?:CR|HM|MM|PM|RM|RS|UR)\d+\s*', '', search)
    for book, type, page in maps:
        search_terms.append(
            and_(
                Map.book == int(book), MapType.abbrev == type,
                Map.page <= int(page), Map.page + Map.npages > int(page))
        )

    # split into multiple independent searches terms
    for prefix, term in  re.findall('([+-])?\s*([^+-]+)', search):

        # parse surveyor, client, date, desc & maptype in double quotes
        desc = re.findall('(BY|FOR|DATE|DESC|(?:MAP)?TYPE)[=:]"(.*?)(?<!")"(?!")', term)
        # replace two consecutive double quotes with a single double quote
        desc = [(s[0], re.sub('""', '"', s[1])) for s in desc]
        # remove description terms in double quotes
        term = re.sub('(?:BY|FOR|DATE|DESC|MAPTYPE)[=:]".*?(?<!")"(?!")', '', term)

        # parse single word surveyor, client, date, desc & maptype without quotes
        desc = re.findall('(BY|FOR|DATE|DESC|(?:MAP)?TYPE)[=:](\S+)', term)
        # remove single word description terms
        term = re.sub('(?:BY|FOR|DATE|DESC|MAPTYPE)[=:]\S+', '', term)

        # township/range/sections should be all that's left
        trs = township_range_section(term) if term != '' else None

        t = []
        for f, d in desc:
            if f =='BY':
                print('by="%s"' % d)
                t.append(and_(Surveyor.fullname.op('~')(d)))
            elif f == 'FOR':
                t.append(and_(Map.client.op('~')(d)))
            elif f == 'DATE':
                dates = parse_dates(d)
                if dates:
                    t.append(and_(Map.recdate >= dates[0]))
                    t.append(and_(Map.recdate <= dates[1]))
            elif f == 'DESC':
                t.append(and_(Map.description.op('~')(d)))
            elif f[-4:] == 'TYPE':
                t.append(and_(MapType.abbrev.op('~')(d)))

        if trs:
            t.append(and_(TRS.tshp == trs['tshp'], TRS.rng == trs['rng']))
            secs = []
            for sec in trs['secs']:

                if sec['subsec']:
                    secs.append(and_(TRS.sec == sec['sec'], TRS.subsec.op('&')(sec['subsec']) != 0))
                else:
                    secs.append(and_(TRS.sec == sec['sec']))
            if secs:
                t.append(or_(*secs))

        if t:
            search_terms.append(and_(*t))

    if search_terms:
        query = db_session.query(Map).join(TRS).join(MapType)
        query = query.outerjoin(Surveyor)           # surveyor can be null
        query = query.filter(or_(*search_terms))
        query = query.order_by(MapType.maptype, Map.recdate.desc(), Map.page.desc())
        results = query.all()

    else:
        results = None

    return results

if __name__ == '__main__':

    srch = 's/2 s32 t7n r1e + n/2 s5 t6n r1e'
    srch = 'ne/4 s5 t6n r1e'
    srch = 'desc:".*"".*"'
    srch = 'se/4 s3 t4n r1e desc="patrick" by="crive""lli"'
    srch = 's5 t6n r1e - ne/4 s5 t6n r1e'
    srch = 'date:6/2001'
    srch = 'type=rm ne/4 s5 t6n r1e by=schillinger'
    srch = 'type=rm ne/4 s5 t6n r1e 11rm5'
    srch = 'type=rm ne/4 s5 t6n r1e 11rm5 69rs30 69rs11 34rs58'
    srch = '11rm5 69rs30 69rs11 34rs58'
    srch = 'desc:\' type:(?!UR|RS|PM)..'

    print('search: >>>%s<<<' % (srch))
    results = do_search(srch)

    if results:
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

    else:
        print('Nothing found.')

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


    assert subsec_bits('NE/4') == 0x00CC
    assert subsec_bits('NE/4 NE/4') == 0x0008
    assert subsec_bits('SE/4 NE/4') == 0x0080
    assert subsec_bits('SW/4 NE/4') == 0x0040
    assert subsec_bits('NW/4 NE/4') == 0x0004
    assert subsec_bits('N/2 NE/4') == 0x000C
    assert subsec_bits('S/2 NE/4') == 0x00C0
    assert subsec_bits('E/2 NE/4') == 0x0088
    assert subsec_bits('W/2 NE/4') == 0x0044
    assert subsec_bits('SE/4') == 0xCC00
    assert subsec_bits('NE/4 SE/4') == 0x0800
    assert subsec_bits('SE/4 SE/4') == 0x8000
    assert subsec_bits('SW/4 SE/4') == 0x4000
    assert subsec_bits('NW/4 SE/4') == 0x0400
    assert subsec_bits('N/2 SE/4') == 0x0C00
    assert subsec_bits('S/2 SE/4') == 0xC000
    assert subsec_bits('E/2 SE/4') == 0x8800
    assert subsec_bits('W/2 SE/4') == 0x4400
    assert subsec_bits('SW/4') == 0x3300
    assert subsec_bits('NE/4 SW/4') == 0x0200
    assert subsec_bits('SE/4 SW/4') == 0x2000
    assert subsec_bits('SW/4 SW/4') == 0x1000
    assert subsec_bits('NW/4 SW/4') == 0x0100
    assert subsec_bits('N/2 SW/4') == 0x0300
    assert subsec_bits('S/2 SW/4') == 0x3000
    assert subsec_bits('E/2 SW/4') == 0x2200
    assert subsec_bits('W/2 SW/4') == 0x1100
    assert subsec_bits('NW/4') == 0x0033
    assert subsec_bits('NE/4 NW/4') == 0x0002
    assert subsec_bits('SE/4 NW/4') == 0x0020
    assert subsec_bits('SW/4 NW/4') == 0x0010
    assert subsec_bits('NW/4 NW/4') == 0x0001
    assert subsec_bits('N/2 NW/4') == 0x0003
    assert subsec_bits('S/2 NW/4') == 0x0030
    assert subsec_bits('E/2 NW/4') == 0x0022
    assert subsec_bits('W/2 NW/4') == 0x0011
    assert subsec_bits('N/2') == 0x00FF
    assert subsec_bits('NE/4 N/2') is None
    assert subsec_bits('SE/4 N/2') is None
    assert subsec_bits('SW/4 N/2') is None
    assert subsec_bits('NW/4 N/2') is None
    assert subsec_bits('N/2 N/2') == 0x000F
    assert subsec_bits('S/2 N/2') == 0x00F0
    assert subsec_bits('E/2 N/2') is None
    assert subsec_bits('W/2 N/2') is None
    assert subsec_bits('S/2') == 0xFF00
    assert subsec_bits('NE/4 S/2') is None
    assert subsec_bits('SE/4 S/2') is None
    assert subsec_bits('SW/4 S/2') is None
    assert subsec_bits('NW/4 S/2') is None
    assert subsec_bits('N/2 S/2') == 0x0F00
    assert subsec_bits('S/2 S/2') == 0xF000
    assert subsec_bits('E/2 S/2') is None
    assert subsec_bits('W/2 S/2') is None
    assert subsec_bits('E/2') == 0xCCCC
    assert subsec_bits('NE/4 E/2') is None
    assert subsec_bits('SE/4 E/2') is None
    assert subsec_bits('SW/4 E/2') is None
    assert subsec_bits('NW/4 E/2') is None
    assert subsec_bits('N/2 E/2') is None
    assert subsec_bits('S/2 E/2') is None
    assert subsec_bits('E/2 E/2') == 0x8888
    assert subsec_bits('W/2 E/2') == 0x4444
    assert subsec_bits('W/2') == 0x3333
    assert subsec_bits('NE/4 W/2') is None
    assert subsec_bits('SE/4 W/2') is None
    assert subsec_bits('SW/4 W/2') is None
    assert subsec_bits('NW/4 W/2') is None
    assert subsec_bits('N/2 W/2') is None
    assert subsec_bits('S/2 W/2') is None
    assert subsec_bits('E/2 W/2') == 0x2222
    assert subsec_bits('W/2 W/2') == 0x1111


