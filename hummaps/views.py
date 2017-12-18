from flask import request, make_response
from flask import render_template, flash, jsonify

from hummaps import app
from hummaps.search import do_search, ParseError
from hummaps.xhr import xhr_request

from hummaps.gpx import gpx_read, gpx_out
from hummaps.gpx import dxf_read, dxf_out
from hummaps.gpx import pnts_read, pnts_out

import os.path


# Custom filter for the Jinja2 template processor
@app.template_filter('basename')
def basename_filter(s):
    return os.path.basename(s)

@app.route('/', methods=['GET', 'POST'])
def index():
    args = request.args
    if request.is_xhr:
        return jsonify(xhr_request(args.get('req', '')))
    elif request.method == 'POST':
        form = request.form
    else:
        form = None

    q = args.get('q', '')
    if q == '':
        return render_template('index.html', query='', results=[])

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
        srid = int(request.form['srid'])
        outfile = request.form['filename']
        if outfile:
            i = outfile.rfind('.')
            if i > 0:
                outfile = outfile[0:i]  # strip extension
        else:
            outfile = 'results'
        # files = request.files.getlist('file')
        # headers = 'type: ' + datatype + ', srid: ' + str(srid) + ', files: ' + ', '.join([f.filename for f in files]) + '\n'
        geom = []
        for f in request.files.getlist('file'):
            filename = f.filename
            ext = filename.lower().rsplit('.', 1)[-1]
            if ext == 'txt':
                geom += pnts_read(f.stream, srid)
            elif ext == 'dxf':
                geom += dxf_read(f.stream, srid)
            elif ext == 'gpx':
                geom += gpx_read(f.stream)
        if datatype == 'pnts':
            resp = make_response(pnts_out(geom, srid))
            outfile += '.txt'
        elif datatype == 'dxf':
            resp = make_response(dxf_out(geom, srid))
            outfile += '.dxf'
        elif datatype == 'gpx':
            resp = make_response(gpx_out(geom))
            outfile += '.gpx'
        else:
            return('Bad type: %s' % datatype, 400)

        resp.headers['Content-Disposition'] = 'attachment; filename="%s"' % outfile
        resp.mimetype = 'application/octet-stream'
        return resp

    return render_template('gpx.html')

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
