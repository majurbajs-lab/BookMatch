"""Runs on PythonAnywhere to write the WSGI config file."""
wsgi = """\
import os, sys

path = '/home/BookMatch/BookMatch'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'bookmatch.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
"""

dest = '/var/www/bookmatch_pythonanywhere_com_wsgi.py'
with open(dest, 'w') as f:
    f.write(wsgi)
print('WSGI file written to', dest)
