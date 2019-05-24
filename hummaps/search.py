import re
from datetime import date
import calendar
from sqlalchemy import and_, or_, not_, between
from sqlalchemy_utils import Ltree

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage


class ParseError(Exception):
    def __init__(self, err, term=''):
        self.err = err
        self.term = term

    def __str__(self):
        if self.term:
            return '%s: %s' % (self.term, self.err)
        else:
            return self.err


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
        raise ParseError(date_str)

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


def subsec_codes(subsec_str):

    # codes for first (right) term
    q_code = {
        'NE': 'CDGH', 'SE': 'KLOP', 'SW': 'IJMN', 'NW': 'ABEF',
        'N': 'ABCDEFGH', 'S': 'IJKLMNOP', 'E': 'CDGHKLOP', 'W': 'ABEFIJMN'
    }

    # codes for second (left) term
    qq_code = {
        'NE': 'BDJL', 'SE': 'FHNP', 'SW': 'EGMO', 'NW': 'ACIK',
        'N': 'ABCDIJKL', 'S': 'EFGHMNOP', 'E': 'BDFHJLNP', 'W': 'ACEGIKMO'
    }

    if re.search('1/1', subsec_str):
        return 'ABCDEFGHIJKLMNOP'       # all subsections

    ss = subsec_str.upper().strip()

    # xx/4 and xx/4 xx/4
    m = re.fullmatch('(?:([NS][EW])/4\s+)?([NS][EW])/4', ss)
    if m:
        qq, q = m.groups()
        return q_code[q] if qq is None else ''.join(sorted(set(q_code[q]).intersection(qq_code[qq])))

    # x/2 and x/2 x/2
    m = re.fullmatch('(?:([NSEW])/2\s+)?([NSEW])/2', ss)
    if m:
        qq, q = m.groups()
        if qq and re.match('E[NS]|[NS]W', ''.join(sorted([q, qq]))):
            # this algorithm doesn't work for N/2 E/2, etc (and it shouldn't have to)
            return None
        return q_code[q] if qq is None else ''.join(sorted(set(q_code[q]).intersection(qq_code[qq])))

    # x/2 xx/4
    m = re.fullmatch('([NSEW])/2\s+([NS][EW])/4', ss)
    if m:
        qq, q = m.groups()
        return ''.join(sorted(set(q_code[q]).intersection(qq_code[qq])))

    return None


def do_search(search):

    # subqueries for the UNION/EXCEPT
    subq_union = []
    subq_except = []

    # split into multiple independent union/exclude search terms
    for prefix, term in re.findall('([+-])?([^+-]+)', search):

        # a list of subterms for this union/exclude term
        subterms = []

        # parse for surveyor, client, date, desc & maptype in double quotes
        pat = '((BY|FOR|REC|DATE|DESC|TYPE|ID|ANY)[=:]"(.*?)(?<!")"(?!"))'
        dquotes = re.findall(pat, term, flags=re.I)
        # replace two consecutive double quotes with a single double quote
        kwterms = [(s[0], s[1], re.sub('""', '"', s[2])) for s in dquotes]
        # empty search "" becomes a double quote which is a valid search
        subterms += kwterms
        term = re.sub(pat, '', term, flags=re.I)

        # parse for surveyor, client, date & desc with empty double quotes
        pat = '((BY|FOR|REC|DATE|DESC)[=:]"()")'
        subterms += re.findall(pat, term, flags=re.I)
        term = re.sub(pat, '', term, flags=re.I)

        # parse for single word surveyor, client, date, desc & maptype without quotes
        pat = '((BY|FOR|REC|DATE|DESC|TYPE|ID|ANY)[=:](\S*))'
        kwterms = re.findall(pat, term, flags=re.I)
        for t, k, v in kwterms:
            if v == '':
                raise ParseError(t)
        subterms += kwterms
        term = re.sub(pat, '', term, flags=re.I)

        # parse for individual maps
        # pat = '((\d+)(CR|HM|MM|PM|RM|RS|UR)(\d+),?)'  # no more commas
        pat = '(\d+)(CR|HM|MM|PM|RM|M|SM|MAPS|RS|S|UR)(\d+)'
        subterms += [(m[0], 'MAP', m[0:]) for m in re.findall(pat, term, flags=re.I)]
        term = re.sub(pat, '', term, flags=re.I)

        # parse for parcel maps
        pat = 'PM\d+'
        subterms += [(m, 'PM', m) for m in re.findall(pat, term, flags=re.I)]
        term = re.sub(pat, '', term, flags=re.I)

        # parse for tract maps
        pat = 'TR\d+'
        subterms += [(m, 'TR', m) for m in re.findall(pat, term, flags=re.I)]
        term = re.sub(pat, '', term, flags=re.I)

        # parse township/range/sections
        ss_pat = '(?:[NS][WE]/4|[NSEW]/2|1/1)'
        sec_pat = '(?:(?:{ss_pat}\s+)?{ss_pat}\s+)?S\d{{1,2}}'.format(ss_pat=ss_pat)
        # trs_pat = '((?:{sec_pat},?\s*)+)(T\d{{1,2}}[NS])\s+(R\d{{1}}[EW])'.format(sec_pat=sec_pat)
        # trs_pat = '((?:{sec_pat},?\s*)+)T?(\d{{1,2}}[NS])(?:,\s*|\s+)R?(\d{{1,2}}[EW])'.format(sec_pat=sec_pat)
        trs_pat = '((?:{sec_pat},?\s*)*)T?(\d{{1,2}}[NS])(?:,\s*|\s+)R?(\d{{1,2}}[EW])'.format(sec_pat=sec_pat)
        m = re.search(trs_pat, term, flags=re.I)
        if m:
            term = term[:m.start()] + term[m.end():]
            trs = {'tshp': m.group(2), 'rng': m.group(3), 'secs': []}
            trs_str = m.group(0)

            # parse the sections/subsections
            sec_pat = '((?:{ss_pat}\s+)?{ss_pat}\s+)?(S\d{{1,2}})'.format(ss_pat=ss_pat)
            for ss, s in re.findall(sec_pat, m.group(1), flags=re.I):
                if ss:
                    subsec = subsec_codes(ss)
                    if subsec is None:
                        raise ParseError(ss, trs_str)
                else:
                    subsec = None
                sec = s[1:]
                if not 1 <= int(sec) <= 36:
                    raise ParseError(s, trs_str)
                trs['secs'].append({'sec': sec, 'subsec': subsec})

            subterms.append((trs_str, 'TRS', trs))

        # shouldn't be anything left at this point
        # term = term.strip()
        # if term:
        #     if term == search.strip():
        #         raise ParseError(search)
        #     else:
        #         raise ParseError(term, search)

        # anything left at this point throw into an ANY term
        term = term.strip()
        if term:
            subterms.append([term, 'ANY', re.sub('\s+', '.*', term)])

        # lists of 'OR' and 'AND' elements
        or_terms = []
        and_terms = []

        # keys and search terms
        # for terms that will be eventually processed by a postgresql regular expression
        # we try to compile here and redirect any exception to a ParseError
        for term, k, v in subterms:
            k = k.upper()
            if k == 'BY':
                try: re.compile(v)
                except: raise ParseError(v, term)
                m = re.match('(P?LS|R?CE)?([\d.?*]+)', v, flags=re.I)
                if m:
                    type, number = m.groups()
                    if type is None:
                        # pattern search both pls and rce
                        and_terms.append(or_(Surveyor.pls.op('~*')(v), Surveyor.rce.op('~*')(v)))
                    elif type.upper()[-2:] == 'LS':
                        and_terms.append(Surveyor.pls.op('~*')(number))
                    else:
                        and_terms.append(Surveyor.rce.op('~*')(number))
                elif v == '':
                    and_terms.append(Surveyor.fullname == None)
                else:
                    # replace spaces with wildcards and pattern search fullname
                    if v.strip().find(' ') < 0:
                        # pattern search full name
                        and_terms.append(Surveyor.fullname.op('~*')(v))
                    else:
                        # assume each non-space fragment starts a word
                        # add wildcards and word boundary qualifiers
                        vqual = '\m' + re.sub('\s+', '.*\m', v)
                        and_terms.append(Surveyor.fullname.op('~*')(vqual))
            elif k == 'DATE' or k == 'REC':
                if v == '':
                    and_terms.append(Map.recdate == None)
                else:
                    dates = parse_dates(v)
                    and_terms.append(between(Map.recdate, *dates))
            elif k == 'FOR':
                if v == '':
                    and_terms.append(Map.client == None)
                else:
                    try: re.compile(v)
                    except: raise ParseError(v, term)
                    and_terms.append(Map.client.op('~*')(v))
            elif k == 'DESC':
                if v == '':
                    and_terms.append(Map.description == None)
                else:
                    try: re.compile(v)
                    except: raise ParseError(v, term)
                    and_terms.append(Map.description.op('~*')(v))
            elif k == 'ANY':
                try:
                    re.compile(v)
                except:
                    raise ParseError(v, term)
                and_terms.append(
                    or_(Map.client.op('~*')(v), Map.description.op('~*')(v))
                )
            elif k == 'TYPE':
                try: re.compile(v)
                except: raise ParseError(v, term)
                and_terms.append(MapType.abbrev.op('~*')(v))
            elif k == 'ID':
                and_terms.append(Map.id == v)
            elif k == 'MAP':
                book, maptype, page = v
                maptype = maptype.upper()
                if maptype == 'M' or maptype == 'MAPS' or maptype == 'SM':
                    maptype = 'RM'
                elif maptype == 'S':
                    maptype = 'RS'
                or_terms.append(
                    and_(
                        Map.book == int(book), MapType.abbrev == maptype,
                        Map.page <= int(page), Map.page + Map.npages > int(page))
                )
            elif k == 'PM':
                or_terms.append(Map.client.op('~*')('\(%s\)(\s\w+)*$' % v))
            elif k == 'TR':
                or_terms.append(Map.client.op('~*')('\(%s\)(\s\w+)*$' % v))
            elif k == 'TRS':
                tshp = (v['tshp'] + '.' + v['rng']).upper()
                if len(v['secs']) == 0:
                    and_terms.append(TRS.trs_path.op('<@')(Ltree(tshp)))
                else:
                    sec_terms = []
                    subsec_paths = []
                    for sec in v['secs']:
                        path = tshp + '.' + sec['sec']
                        if sec['subsec'] is None:
                            sec_terms.append(TRS.trs_path.op('<@')(Ltree(path)))
                        else:
                            for code in sec['subsec']:
                                subsec_paths.append(Ltree(path + '.' + code))
                    sec_terms.append(TRS.trs_path.in_(subsec_paths))
                    and_terms.append(or_(*sec_terms))

        if and_terms:
            or_terms.append(and_(*and_terms))
        if or_terms:
            q = db_session.query(Map.id).join(MapType).outerjoin(TRS)
            q = q.outerjoin(Surveyor, Map.surveyor)
            q = q.filter(or_(*or_terms))
            if prefix == '-':
                subq_except.append(q)
            else:
                subq_union.append(q)

    if subq_union:
        query = db_session.query(Map).join(MapType).outerjoin(TRS)
        query = query.outerjoin(Surveyor, Map.surveyor)
        subq = subq_union.pop(0)
        for q in subq_union:
            subq = subq.union(q)
        for q in subq_except:
            subq = subq.except_(q)
        query = query.filter(Map.id.in_(subq))
        query = query.order_by(MapType.maptype, Map.recdate.desc(), Map.book.desc(), Map.page.desc())

        return query.all()
    else:
        return []


if __name__ == '__main__':

    assert subsec_codes('NE/4') == 'CDGH'
    assert subsec_codes('NE/4 NE/4') == 'D'
    assert subsec_codes('SE/4 NE/4') == 'H'
    assert subsec_codes('SW/4 NE/4') == 'G'
    assert subsec_codes('NW/4 NE/4') == 'C'
    assert subsec_codes('N/2 NE/4') == 'CD'
    assert subsec_codes('S/2 NE/4') == 'GH'
    assert subsec_codes('E/2 NE/4') == 'DH'
    assert subsec_codes('W/2 NE/4') == 'CG'
    assert subsec_codes('SE/4') == 'KLOP'
    assert subsec_codes('NE/4 SE/4') == 'L'
    assert subsec_codes('SE/4 SE/4') == 'P'
    assert subsec_codes('SW/4 SE/4') == 'O'
    assert subsec_codes('NW/4 SE/4') == 'K'
    assert subsec_codes('N/2 SE/4') == 'KL'
    assert subsec_codes('S/2 SE/4') == 'OP'
    assert subsec_codes('E/2 SE/4') == 'LP'
    assert subsec_codes('W/2 SE/4') == 'KO'
    assert subsec_codes('SW/4') == 'IJMN'
    assert subsec_codes('NE/4 SW/4') == 'J'
    assert subsec_codes('SE/4 SW/4') == 'N'
    assert subsec_codes('SW/4 SW/4') == 'M'
    assert subsec_codes('NW/4 SW/4') == 'I'
    assert subsec_codes('N/2 SW/4') == 'IJ'
    assert subsec_codes('S/2 SW/4') == 'MN'
    assert subsec_codes('E/2 SW/4') == 'JN'
    assert subsec_codes('W/2 SW/4') == 'IM'
    assert subsec_codes('NW/4') == 'ABEF'
    assert subsec_codes('NE/4 NW/4') == 'B'
    assert subsec_codes('SE/4 NW/4') == 'F'
    assert subsec_codes('SW/4 NW/4') == 'E'
    assert subsec_codes('NW/4 NW/4') == 'A'
    assert subsec_codes('N/2 NW/4') == 'AB'
    assert subsec_codes('S/2 NW/4') == 'EF'
    assert subsec_codes('E/2 NW/4') == 'BF'
    assert subsec_codes('W/2 NW/4') == 'AE'
    assert subsec_codes('N/2') == 'ABCDEFGH'
    assert subsec_codes('NE/4 N/2') is None
    assert subsec_codes('SE/4 N/2') is None
    assert subsec_codes('SW/4 N/2') is None
    assert subsec_codes('NW/4 N/2') is None
    assert subsec_codes('N/2 N/2') == 'ABCD'
    assert subsec_codes('S/2 N/2') == 'EFGH'
    assert subsec_codes('E/2 N/2') is None
    assert subsec_codes('W/2 N/2') is None
    assert subsec_codes('S/2') == 'IJKLMNOP'
    assert subsec_codes('NE/4 S/2') is None
    assert subsec_codes('SE/4 S/2') is None
    assert subsec_codes('SW/4 S/2') is None
    assert subsec_codes('NW/4 S/2') is None
    assert subsec_codes('N/2 S/2') == 'IJKL'
    assert subsec_codes('S/2 S/2') == 'MNOP'
    assert subsec_codes('E/2 S/2') is None
    assert subsec_codes('W/2 S/2') is None
    assert subsec_codes('E/2') == 'CDGHKLOP'
    assert subsec_codes('NE/4 E/2') is None
    assert subsec_codes('SE/4 E/2') is None
    assert subsec_codes('SW/4 E/2') is None
    assert subsec_codes('NW/4 E/2') is None
    assert subsec_codes('N/2 E/2') is None
    assert subsec_codes('S/2 E/2') is None
    assert subsec_codes('E/2 E/2') == 'DHLP'
    assert subsec_codes('W/2 E/2') == 'CGKO'
    assert subsec_codes('W/2') == 'ABEFIJMN'
    assert subsec_codes('NE/4 W/2') is None
    assert subsec_codes('SE/4 W/2') is None
    assert subsec_codes('SW/4 W/2') is None
    assert subsec_codes('NW/4 W/2') is None
    assert subsec_codes('N/2 W/2') is None
    assert subsec_codes('S/2 W/2') is None
    assert subsec_codes('E/2 W/2') == 'BFJN'
    assert subsec_codes('W/2 W/2') == 'AEIM'
    assert subsec_codes('1/1') == 'ABCDEFGHIJKLMNOP'

    exit(0)

    # for m in db_session.query(Map).join(Surveyor, Map.surveyor).filter(Surveyor.fullname.op('~*')('crivelli')):
    #     print(m, ', '.join([s.name for s in m.surveyor]))
    #
    # exit(0)

    srch = 'id:15833'
    srch = '1n 5e'
    srch = 'pm1 pm16 pm165 pm1656'
    srch = 'tr9 tr95'
    results = do_search(srch)
    # print('\nsearch: \'%s\' => %s' % (srch, results))
    if results:
        n = len(results)

        for i in range(n):

            map = results[i]

            mapimages = ', '.join([mapimage.imagefile for mapimage in map.mapimages])
            if mapimages == '':
                mapimages = 'None'

            certs = []
            for cc in map.certs:
                imagefiles = ', '.join([ccimage.imagefile for ccimage in cc.ccimages])
                if imagefiles == '':
                    imagefiles = 'None'
                certs.append('CC=%s (%s)' % (cc.doc_number, imagefiles))
            certs = ', '.join(certs)

            print('%2d %6d %s %s %s' % (i + 1, map.id, map.maptype.abbrev.upper(), map.bookpage, map.client))
            # print(map.heading)
            # print(map.line1)
            # print(map.line2)
            # print(map.url())
            # for mapimage in map.mapimages:
            #     print(mapimage.imagefile)
            # print()

        print('results: %d maps found.' % (n))
    else:
        print('Nothing found.')

    # exit(0)

    print()
    search = [
        ('1n 5e', 129),
        ('s36 t2n r5e', 26),
        ('s36 t2n,r5e', 26),
        ('s36 t2n, r5e', 26),
        ('s36 2n 5e', 26),
        ('s30 1n,5e', 23),
        ('s25 s26 s35 s36 2n 5e', 31),
        ('s25,s26,s35,s36 2n 5e', 31),
        ('s25, s26, s35, s36 2n 5e', 31),
        ('1/1 s36 t2n r5e', 5),
        ('s/2 s36 t2n r5e', 5),
        ('sw/4 s36 t2n r5e', 5),
        ('s/2 w/2 s36 t2n r5e', ParseError),
        ('s/2 sw/4 s36 t2n r5e', 5),
        ('n/2 sw/4 s36 t2n r5e', 5),
        ('w/2 sw/4 s36 t2n r5e', 4),
        ('se/4 s36 t2n r5e', 3),
        ('w/2 se/4 s36 t2n r5e + sw/4 s31 t2n r6e', 7),
        ('s36 t2n r5e - w/2 se/4 s36 t2n r5e + s31 t2n r6e - sw/4 s31 t2n r6e', 20),
        ('1/1 s32 t7n r1e', 249),
        ('desc:"', 4),
        ('desc:" ""."" "', 3),
        ('s5 t6n r1e - ne/4 s5 t6n r1e', 199),
        ('s5 t6n r1e - ne/4 s5 t6n r1e -type:cr -type:hm -type:ur', 180),
        ('s5 t6n r1e - ne/4 s5 t6n r1e -type:cr|hm|ur', 180),
        ('+s5 t6n r1e type:rs|rm|pm -ne/4 s5 t6n r1e', 180),
        ('+s5 t6n r1e type:(?!cr|hm|ur).. -ne/4 s5 t6n r1e', 180),
        ('date:2015 by:crivelli + date:2015 by:pulley', 23),
        ('date:2015 by:CrIveLLi|PuLLey', 23),
        ('rec:2/7/1975 by:bushnell', 2),
        ('by="b kolstad"', 81),
        ('by="d a c"', 119),
        ('by:ls9153', 1),
        ('by:9153', 1),
        ('by:rce62665', 1),
        ('by=4829 rec=2/2015', 3),
        ('type=rm ne/4 s5 t6n r1e by=schillinger', 6),
        ('type=rm ne/4 s5 t6n r1e', 34),
        ('11rm5 69rs30 69rs11 34rs58', 4),
        ('type=rm ne/4 s5 t6n r1e', 34),
        ('type=rm ne/4 s5 t6n r1e + 11rm5 69rs30 69rs11 34rs58', 38),
        ('type=rm ne/4 s5 t6n r1e 11rm5 69rs30 69rs11 34rs58', 38),
        ('5cr45 2hm90 1mm100 45rs100 16pm10 19rm30 1ur150', 7),
        # ('5cr45, 2hm90, 1mm100, 45rs100, 16pm10, 19rm30, 1ur150', 7),
        ('5cr45 2hm90 1mm100 45rs100 16pm10 19rn30 1ur150', 6),
        ('tr95', 3),
        ('tr9 tr95', 4),
        ('pm165', 2),
        ('14maps56', 1),
        ('14sm56', 1),
        ('pm1 pm16 pm165 pm1656', 5),
        ('desc:\d{5}', 100),
        ('any=deerfield.ranch', 6),
        ('any=along.hwy.36', 9),
        ('deerfield ranch', 6),
        ('nothing', 0),
        ('2n 5e by=', ParseError),
        ('for: deerfield', ParseError),
        ('desc:?', ParseError),
    ]

    for srch, result in search:
        try:
            maps = do_search(srch)

        except Exception as e:
            print('\'%s\': %s: %s' % (srch, type(e), str(e)))
            if result is not None and issubclass(result, Exception):
                assert isinstance(e, result)
            elif result is not None:
                raise

        else:
            if result is not None:
                assert len(maps) == result

            print('\'%s\': %d' % (srch, len(maps)))

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

