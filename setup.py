from setuptools import setup

setup(
    name='waste.d',
    version='0.1.0',
    packages=[''],
    url='',
    license='',
    author='Jari Turkia',
    author_email='',
    description='',
    install_requires=[
        'Django',
        'django-extensions',
        'djangorestframework',
        'django-mysql',
        'mysqlclient',
        'google-cloud-core',
        'google-api-core>=1.19.0',
        'google-cloud-ndb',
        'google-cloud-logging',
        'google-cloud-secret-manager',
        'google-cloud-tasks>=2.0',
        'google-api-python-client>=1.12.0',
        'google-auth-oauthlib',
        'lxml',
        'gunicorn>=20.0.4',
        'requests',
    ]
)
