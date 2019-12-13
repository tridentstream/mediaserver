import os

from setuptools import setup, find_packages

from tridentstream import __version__


EXCLUDE_FROM_PACKAGES = ['tridentstream.bin']


setup(
    name='tridentstream',
    version=__version__,
    url='https://github.com/tridentstream/mediaserver',
    author='Anders Jensen',
    author_email='johndoee@tridentstream.org',
    description='Media Streaming Server',
    long_description="TODO",
    license='MIT',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES) + ['twisted.plugins'],
    scripts=[
        'tridentstream/bin/bootstrap-tridentstream',
        # 'tridentstream/bin/tridentstream',
    ],
    package_data={
        '': [
            'tridentstream/fixtures/tridentstream-initial.json',

            'tridentstream/services/webinterface/static/*',
            'tridentstream/services/webinterface/static/*/*',
            'tridentstream/services/webinterface/static/*/*/*',
        ],
    },
    include_package_data=True,
    install_requires=[
        'txasgiresource>=2.0.0',
        'twisted>=17.1.0',
        'service_identity',
        'channels>=2.0.0',
        'Django>=2.0.0,<2.99.99',
        'pytz>=2016.7',
        'django-environ',
        'django-cors-headers>=1.2.2',
        'django-filter>=2.0.0',
        'django-picklefield>=0.3.2',
        'djangorestframework>=3.4.7',
        'djangorestframework-filters>=1.0.0.dev0',
        'djangorestframework-jsonapi>=2.4.0',
        'jsonfield>=1.0.3',
        'scandir>=1.3',
        'requests>=2.11.1',
        'rarfile>=2.7',
        'json-rpc>=1.10.3',
        'Whoosh>=2.7.4',
        'guessit>=2.0.4',
        'pillow',
        'tvdb-api>=2.0,<2.999999',
        'imdbparser',
        'malparser',
        'thomas>=2.2.1',
        'apscheduler',
        'django-cache-url',
        'dj-database-url',
        'wrapt',
        'wampyre>=1.0.1',
        'unplugged>=0.1.4',

        'certifi', # loud errors
    ],
    extras_require={
        'lmdb': [
            'lmdb>=0.89',
        ],
        'leveldb': [
            'leveldb>=0.193',
        ],
        'test': [
            'pytest',
            'pytest-django',
            'freezegun',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Twisted',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
