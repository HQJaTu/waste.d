import os
import sys
import logging

#log = logging.getLogger('wasted_project.settings')
log = logging.getLogger(__name__)

DJANGO_ENV_DEV = 'Development'
DJANGO_ENV_PROD = 'Production'


def module_init():
    pid = os.getpid()

    if 'DJANGO_ENV' not in os.environ:
        if 'runserver' in sys.argv:
            os.environ['DJANGO_ENV'] = DJANGO_ENV_DEV
        else:
            os.environ['DJANGO_ENV'] = DJANGO_ENV_PROD

    # Import environment?
    settings_allowed = [
        'PYTHONUNBUFFERED',
        'GOOGLE_CLOUD_PROJECT',
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GCP_RUN_HOSTS',
        'GCP_STATIC_URL',
        'GCP_TASKS_REGION',
        'GCP_TASKS_SERVICE_ACCOUNT',
        'GCP_TASKS_SERVICE_URL_HOST',
    ]
    if 'DJANGO_ENV' not in os.environ:
        settings_file = '.env'
    else:
        settings_file = '.env-%s' % os.environ['DJANGO_ENV']
        if not os.path.isfile(settings_file) and os.path.isfile('.env'):
            settings_file = '.env'
        if os.environ['DJANGO_ENV'] == DJANGO_ENV_PROD:
            settings_allowed = [
                'PYTHONUNBUFFERED',
                'GCP_RUN_HOSTS',
                'GCP_STATIC_URL',
                'GCP_TASKS_REGION',
                'GCP_TASKS_SERVICE_ACCOUNT',
                'GCP_TASKS_SERVICE_URL_HOST',
            ]
    if os.path.isfile(settings_file):
        with open(settings_file) as f:
            for line in f:
                parts = line.rstrip().split('=', maxsplit=1)
                if not parts or not parts[0]:
                    continue
                if parts[0] not in settings_allowed:
                    log.error('[%d] Invalid setting "%s". Refusing to continue!' % (pid, parts[0]))
                    raise ValueError('Invalid setting "%s"' % parts[0])
                if parts[0] in os.environ:
                    log.warning('[%d] Not overriding existing setting "%s"' % (pid, parts[0]))
                    continue
                log.info("[%d] Setting: %s = '%s'" % (pid, parts[0], parts[1]))
                os.environ[parts[0]] = parts[1]

    if "GCP_RUN_HOSTS" in os.environ:
        log.info("[%d] Adding '%s' as an allowed host" % (pid, os.environ['GCP_RUN_HOSTS']))
    else:
        log.warning("[%d] No known hosts defined! (See env var GCP_RUN_HOSTS.)" % pid)


module_init()
