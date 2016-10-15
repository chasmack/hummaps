import re
from datetime import date
import calendar
from sqlalchemy import and_, or_, not_, between

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage


def parse_dates(date_str):

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
    pat = '(?:(\d+/)(\d+/)?)?(\d{4})(?:\s+(?:(\d+/)(\d+/)?)?(\d{4}))?'
    m = re.fullmatch(pat, date_str.strip())
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


def tshp_num(tshp_str):
    m = re.search('T(\d{1,2})([NS])', tshp_str.upper())
    if m is None:
        return None
    if m.group(2) == 'N':
        return int(m.group(1)) - 1
    else:
        return -1 * int(m.group(1))


def rng_num(rng_str):
    m = re.search('R*(\d{1,2})([EW])', rng_str.upper())
    if m is None:
        return None
    if m.group(2) == 'E':
        return int(m.group(1)) - 1
    else:
        return -1 * int(m.group(1))


def subsec_bits(subsec_str):

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

    if re.search('1/1', subsec_str):
        return 0xffff               # all subsections

    ss = subsec_str.upper().strip()

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


def township_range_section(trs_str):

    # parse off any sections and subsections
    secs = []
    ss_pat = '(?:[NS][WE]/4|[NSEW]/2|1/1)'
    sec_pat = '(?:(?:{ss_pat}\s+)?{ss_pat}\s+)?S\d{{1,2}}'.format(ss_pat=ss_pat)
    for s in re.findall('({sec_pat})(?:,\s*)?'.format(sec_pat=sec_pat), trs_str, flags=re.I):

        pat = '((?:{ss_pat}\s+)?{ss_pat}\s+)?S(\d+)\s*'.format(ss_pat=ss_pat)
        m = re.fullmatch(pat, s, flags=re.I)
        if m is None:
            # return 'Section formatting error: "%s"' % (s)
            return None

        if m.group(1):
            subsec = subsec_bits(m.group(1))
            if subsec is None:
                # return 'Subsection error: "%s"' % (s)
                return None
        else:
            subsec = None
        sec = int(m.group(2))
        if sec == 0 or sec > 36:
            # return 'Section number error: "$s"' % (s)
            return None

        secs.append({'sec': sec, 'subsec': subsec})

    m = re.search('(T\d{1,2}[NS])\s+(R\d{1}[EW])\s*$', trs_str, flags=re.I)
    if m:
        t = tshp_num(m.group(1))
        r = rng_num(m.group(2))
        trs = {'tshp': t, 'rng': r, 'secs': secs}
    else:
        # return 'Township/Range format error: "%s"' % (strm)
        return None

    return trs


def do_search(search):

    # subqueries to for the final UNOIN/EXCEPT
    subq_union = []
    subq_except = []

    # split into multiple independent search terms
    for prefix, term in  re.findall('([+-])?\s*([^+-]+)', search):

        # break independent terms into a list of 'OR' and 'AND' elements
        or_terms = []
        and_terms = []

        # list of keyword search terms
        desc = []

        # parse for surveyor, client, date, desc & maptype in double quotes
        pat = '(BY|FOR|DATE|DESC|(?:MAP)?TYPE)[=:]"(.*?)(?<!")"(?!")'
        dquotes = re.findall(pat, term, flags=re.I)
        # replace two consecutive double quotes with a single double quote
        desc += [(s[0], re.sub('""', '"', s[1])) for s in dquotes]
        term = re.sub(pat, '', term, flags=re.I)

        # parse for single word surveyor, client, date, desc & maptype without quotes
        pat = '(BY|FOR|DATE|DESC|(?:MAP)?TYPE)[=:](\S+)'
        desc += re.findall(pat, term, flags=re.I)
        term = re.sub(pat, '', term, flags=re.I)

        # parse for individual maps
        pat = '(\d+)(CR|HM|MM|PM|RM|RS|UR)(\d+)'
        desc += [('MAP', m) for m in re.findall(pat, term, flags=re.I)]
        term = re.sub(pat, '', term, flags=re.I)

        # parse for township/range/sections
        trs = township_range_section(term)
        if trs:
            desc.append(('TRS', trs))

        for k, d in desc:
            k = k.upper()
            if k =='BY':
                and_terms.append(and_(Surveyor.fullname.op('~*')(d)))
            elif k == 'FOR':
                and_terms.append(and_(Map.client.op('~*')(d)))
            elif k == 'DATE':
                dates = parse_dates(d)
                if dates:
                    and_terms.append(between(Map.recdate, *dates))
            elif k == 'DESC':
                and_terms.append(and_(Map.description.op('~*')(d)))
            elif k[-4:] == 'TYPE':
                and_terms.append(and_(MapType.abbrev.op('~*')(d)))
            elif k == 'MAP':
                book, type, page = d
                or_terms.append(
                    and_(
                        Map.book == int(book), MapType.abbrev == type.upper(),
                        Map.page <= int(page), Map.page + Map.npages > int(page))
                )
            elif k == 'TRS':
                secs = []
                for sec in d['secs']:
                    if sec['subsec']:
                        secs.append(and_(
                            TRS.sec == sec['sec'],
                            TRS.subsec.op('&')(sec['subsec']) > 0))
                    else:
                        secs.append(and_(TRS.sec == sec['sec']))
                and_terms.append(and_(TRS.tshp == d['tshp'], TRS.rng == d['rng'], or_(*secs)))

        if and_terms:
            or_terms.append(and_(*and_terms))
        if or_terms:
            q = db_session.query(Map.id).join(TRS).join(MapType)
            q = q.outerjoin(Surveyor)  # surveyor can be null
            q = q.filter(or_(*or_terms))
            if prefix == '-':
                subq_except.append(q)
            else:
                subq_union.append(q)

    if subq_union:
        query = db_session.query(Map).join(TRS).join(MapType)
        query = query.outerjoin(Surveyor)  # surveyor can be null
        subq = subq_union.pop(0)
        for q in subq_union:
            subq = subq.union(q)
        for q in subq_except:
            subq = subq.except_(q)
        query = query.filter(Map.id.in_(subq))
        query = query.order_by(MapType.maptype, Map.recdate.desc(), Map.page.desc())
        results = query.all()

    else:
        results = None

    return results

if __name__ == '__main__':

    search = [
        's36 t2n r5e',
        '1/1 s36 t2n r5e',
        'n/2 s36 t2n r5e + s/2 s36 t2n r5e',
        'se/4 s36 t2n r5e',
        'w/2 se/4 s36 t2n r5e + sw/4 s31 t2n r6e',
        's36 t2n r5e - w/2 se/4 s36 t2n r5e + s31 t2n r6e - sw/4 s31 t2n r6e',
        '1/1 s32 t7n r1e',
        'desc:".*"".*"',
        'desc:"',
        's5 t6n r1e - ne/4 s5 t6n r1e',
        's5 t6n r1e - ne/4 s5 t6n r1e -type:cr -type:hm -type:ur',
        's5 t6n r1e - ne/4 s5 t6n r1e -type:cr|hm|ur',
        '+s5 t6n r1e type:rs|rm|pm -ne/4 s5 t6n r1e',
        '+s5 t6n r1e type:(?!cr|hm|ur).. -ne/4 s5 t6n r1e',
        'date:2015 by:crivelli + date:2015 by:pulley',
        'date:2015 by:CrIveLLi|PuLLey',
        'type=rm ne/4 s5 t6n r1e by=schillinger',
        'type=rm ne/4 s5 t6n r1e',
        '11rm5 69rs30 69rs11 34rs58',
        'type=rm ne/4 s5 t6n r1e + 11rm5 69rs30 69rs11 34rs58',
        'type=rm ne/4 s5 t6n r1e 11rm5 69rs30 69rs11 34rs58',
        '11rm5 69rs30 69rs11 34rs58',
        'desc:\d{5}'
    ]

    for srch in search:
        results = do_search(srch)

        print('%d, \'%s\'' % (len(results) if results else 0, srch))

    exit(0)

    srch = 'ne/4 s5 t6n r1e'
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


