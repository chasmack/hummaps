from flask import request, make_response, send_from_directory
from flask import render_template, flash
from flask.json import jsonify, dumps

from hummaps import app
from hummaps.xhr import xhr_request
from hummaps.search import do_search, ParseError

from hummaps.gpx import gpx_in, gpx_out
from hummaps.gpx import pnezd_in, pnezd_out

from hummaps.polycalc import process_line_data

import os.path
from time import time


# Custom filter for the Jinja2 template processor
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)


# Index of available tools.
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


# Map image files.
@app.route('/hummaps/map/<path:path>', methods=['GET'])
def send_map_image(path):
    return send_from_directory('map', path)


# Map pdf files.
@app.route('/hummaps/pdf/<path:path>', methods=['GET'])
def send_map_pdf(path):
    return send_from_directory('pdf', path)


# hummaps - the Humboldt County map index.
@app.route('/hummaps', methods=['GET', 'POST'])
def hummaps():

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
        return render_template('hummaps.html', query='', results=[])

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

    return render_template('hummaps.html', query=q, form=form, results=results, total=total)


# polycalc - generate DXF linework from a command file.
@app.route('/polycalc', methods=['GET', 'POST'])
def polycalc():
    if request.method == 'GET':
        return render_template('polycalc.html')
    try:
        f = request.files.get('file')
        dxf, listing = process_line_data(f.stream)
    except Exception as err:
        return (jsonify(error=str(err)), 400)

    filename = 'results.dxf'

    resp = make_response(jsonify(filename=filename, dxf=dxf, listing='\n'.join(listing)))
    # resp.headers['Content-Disposition'] = 'attachment; filename="%s"' % outfile
    # resp.mimetype = 'application/octet-stream'
    # resp.cache_control.no_cache = True
    # resp.cache_control.no_store = True
    return resp


# gpx - transform between PNEZD points and GPX waypoints.
@app.route('/gpx', methods=['GET', 'POST'])
def gpx():
    if request.method == 'GET':
        return render_template('gpx.html')

    # XHR request
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

    try:
        pnts = []
        for f in request.files.getlist('file'):
            if f.filename.endswith('.txt'):
                pnts += pnezd_in(f.stream, target_srid)
            elif f.filename.endswith('.gpx'):
                pnts += gpx_in(f.stream, nad83=nad83)
            else:
                raise TypeError('Unsupported file type: "%s"' % f.filename)

        if datatype == 'pnts':
            resp = make_response(pnezd_out(pnts, target_srid))
            outfile += '.txt'
        elif datatype == 'gpx':
            resp = make_response(gpx_out(pnts, nad83=nad83))
            outfile += '.gpx'
        else:
            raise TypeError('Bad request data type: "%s"' % datatype)

    except Exception as err:
        return (jsonify(error=str(err)), 400)

    resp.headers['Content-Disposition'] = 'attachment; filename="%s"' % outfile
    resp.mimetype = 'application/octet-stream'
    resp.cache_control.no_cache = True
    resp.cache_control.no_store = True
    return resp


#
# Service unavailable
#

@app.route('/error/503.html', methods=['GET'])
def unavailable():
    return render_template('503.html'), 503

#
# /robots.txt
#

# @app.route ('/robots.txt')
# def robots_txt():
#     txt = ''.join((
#         'User-agent: *\r\n',
#         'Disallow: /\r\n'
#     ))
#     return make_response(txt)

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

