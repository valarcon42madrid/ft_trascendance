#!/usr/bin/env python
#manage.py mysite base !!!!!!!!!!!
"""Django's command-line utility for administrative tasks."""
import os
import sys

#from django.core.wsgi import get_wsgi_application # ????????????? antes no

#application = get_wsgi_application() # ????????????????????? antes no
    
def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    #os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true" # antes no
    #application = get_wsgi_application() # ????????????????????? antes no
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
