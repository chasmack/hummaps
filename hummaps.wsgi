import sys, os

app_root   = os.path.realpath(os.path.dirname(__file__))
python_env = os.path.realpath('C:/Anaconda3/envs/py34')

sys.path = [
    app_root,
    app_root,
    os.path.join(python_env, 'python34.zip'),
    os.path.join(python_env, 'DLLs'),
    os.path.join(python_env, 'Lib'),
    os.path.join(python_env, ''),
    os.path.join(python_env, r'Lib\site-packages'),
    os.path.join(python_env, r'Lib\site-packages\setuptools-20.7.0-py3.4.egg'),
]

from hummaps import app as application
