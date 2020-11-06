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
        'google-cloud-core',
        'google-api-core>=1.19.0',
        'google-cloud-ndb',
        'google-cloud-logging',
        'lxml',
        'gunicorn>=20.0.4',
    ]
)
