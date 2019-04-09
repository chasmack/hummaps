from flask import request, make_response
from flask import render_template, flash
from flask.json import jsonify, dumps

import tempfile

from hummaps import app
from hummaps.xhr import xhr_request
# from hummaps.search import do_search, ParseError
from hummaps.search_paths import do_search, ParseError

from hummaps.gpx import gpx_in, gpx_out
from hummaps.gpx import pnezd_in, pnezd_out

import os.path
from time import time

# Custom filter for the Jinja2 template processor
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)

@app.route('/', methods=['GET', 'POST'])
def index():

    args = request.args
    if request.is_xhr:
        resp = jsonify(xhr_request(args.get('req', '')))
        resp.cache_control.public = True
        resp.cache_control.max_age = 3600
        resp.expires = int(time() + 3600)
        return resp
    elif request.method == 'POST':
        form = request.form
    else:
        form = None

    q = args.get('q', '')
    if q == '':
        return render_template('index.html', query='', results=[])

        # Server side processing of form data
        # if form:
        #     q = ' '.join([form['section'], form['township'], form['range']]).strip();
        #     if form['recdate']:
        #         if form['recdate-to']:
        #             q += ' date="' + form['recdate'] + ' ' + form['recdate-to'] + '"'
        #         else:
        #             q += ' date="' + form['recdate'] + '"'
        #     if form['surveyor']:
        #         q += ' by="' + re.sub(r'\s*\(.*', '', form['surveyor']) + '"'
        #     if form['client']:
        #         q += ' for="' + form['client'] + '"'
        #     if form['description']:
        #         q += ' desc="' + form['description'] + '"'
        #     if q:
        #         maptypes = []
        #         for t in ('cr', 'pm', 'rm', 'rs', 'ur'):
        #             if 'maptype-' + t in form:
        #                 maptypes.append(t)
        #         if 'maptype-other' in form:
        #             maptypes += ['hm|mm']
        #         if maptypes and len(maptypes) < 6:
        #             q += ' type=' + '|'.join(maptypes)
        #     if form['maps']:
        #         q = ' '.join([q, form['maps']])

    results = []
    try:
        results = do_search(q)
    except ParseError as e:
        term = ' (%s)' % e.term if e.term else ''
        flash('Search error%s: <strong>%s</strong>' % (term, e.err), 'error')
    except Exception as e:
        flash('Search error: <strong>%s</strong>' % str(e), 'error')

    total = len(results)
    if total > 200:
        results = results[0:200]

    return render_template('index.html', query=q, form=form, results=results, total=total)


@app.route('/gpx', methods=['GET', 'POST'])
def gpx():
    if request.method == 'POST':

        datatype = request.form['datatype']
        target_srid = int(request.form['srid'])
        outfile = request.form['filename']
        nad83 = request.form.get('nad83', None)
        if outfile:
            i = outfile.rfind('.')
            if i > 0:
                outfile = outfile[0:i]  # strip extension
        else:
            outfile = 'results'

        # files = request.files.getlist('file')
        # headers = 'type: ' + datatype + ', srid: ' + str(srid) + ', files: ' + ', '.join([f.filename for f in files]) + '\n'

        pnts = []

        for f in request.files.getlist('file'):
            filename = f.filename
            ext = filename.lower().rsplit('.', 1)[-1]
            if ext == 'txt':
                pnts += pnezd_in(f.stream, target_srid)
            elif ext == 'gpx':
                pnts += gpx_in(f.stream, nad83=nad83)
        if datatype == 'pnts':
            resp = make_response(pnezd_out(pnts, target_srid))
            outfile += '.txt'
        elif datatype == 'gpx':
            resp = make_response(gpx_out(pnts, nad83=nad83))
            outfile += '.gpx'
        else:
            return('Bad type: %s' % datatype, 400)

        resp.headers['Content-Disposition'] = 'attachment; filename="%s"' % outfile
        resp.mimetype = 'application/octet-stream'
        resp.cache_control.no_cache = True
        resp.cache_control.no_store = True
        return resp

    return render_template('gpx.html')

#
# Service unavailable
#

@app.route('/error/503.html', methods=['GET'])
def unavailable():
    return render_template('503.html'), 503

#
# /robots.txt
#

@app.route ('/robots.txt')
def robots_txt():
    txt = ''.join((
        'User-agent: *\n',
        'Disallow: /map/\n',
        'Disallow: /pdf/\n',
        'Disallow: /scan/\n'
    ))
    return make_response(txt)

#
# HTTP error handlers
#

@app.errorhandler(400)
def bad_request(e):
    return render_template('400.html'), 400

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

