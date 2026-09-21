"""WSGI config for travel_booking project."""

import os
import time

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_booking.settings')

from django.core.wsgi import get_wsgi_application


def _run_migrations_once():
    """Apply pending schema migrations before this process starts serving.

    The production SQLite database lives on Render's ephemeral filesystem,
    which is recreated on every deploy, so the schema must be re-applied at
    process startup — even if the deploy pipeline's build command is not
    honoured. The lock file serialises Gunicorn's worker processes so only one
    runs ``migrate`` (SQLite can only handle one writer at a time).
    """
    import django
    django.setup()

    from django.conf import settings

    if settings.DEBUG:
        return

    lock_path = os.path.join(settings.BASE_DIR, '.migrate.lock')
    try:
        deadline = time.time() + 60
        while True:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                break
            except FileExistsError:
                if time.time() > deadline:
                    break
                time.sleep(0.5)
    except OSError:
        pass

    from django.db import connection
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False, verbosity=0)
    finally:
        try:
            os.remove(lock_path)
        except OSError:
            pass
        connection.close()


_run_migrations_once()

application = get_wsgi_application()