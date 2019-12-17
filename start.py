from hummaps import app
from waitress import serve

if __name__ == '__main__':

    # app.run(host='0.0.0.0', port=80, debug=True)
    serve(app, listen='0.0.0.0:80', url_prefix='/tools')
