import os

from setuptools import setup, find_packages

from tridentstream import __version__


EXCLUDE_FROM_PACKAGES = ['tridentstream.bin']

def readme():
    with open("README.rst") as f:
        return f.read()

setup(
    name='tridentstream',
    version=__version__,
    url='https://github.com/tridentstream/mediaserver',
    author='Anders Jensen',
    author_email='johndoee@tridentstream.org',
    description='Media Streaming Server',
    long_description=readme(),
    long_description_content_type="text/x-rst",
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
        'txasgiresource>=2.0.0,<2.99.99',
        'twisted>=19.10.0,<19.99.99',
        'service-identity>=18.1.0,<18.99.99',
        'channels>=2.0.0,<2.99.99',
        'Django>=2.0.0,<2.99.99',
        'pytz>=2019.3',
        'django-environ>=0.4.5,<0.4.99',
        'django-cors-headers>=3.2.0,<3.99.99',
        'django-filter>=2.2.0,<2.99.99',
        'django-picklefield>=2.0,<2.99',
        'djangorestframework>=3.11.0,<3.11.99',
        'djangorestframework-filters>=1.0.0.dev0',
        'djangorestframework-jsonapi>=3.0.0,<3.99.99',
        'jsonfield>=2.0.2,<2.99.99',
        'requests>=2.11.1',
        'rarfile>=3.1,<3.99',
        'json-rpc>=1.12.2,<1.12.99',
        'Whoosh>=2.7.4,<2.7.99',
        'guessit>=3.1.0,<3.1.99',
        'tvdb-api>=2.0,<2.999999',
        'apscheduler>=3.6.3,<3.6.99',
        'wrapt>=1.11.2,<1.11.99',
        'wampyre>=1.1.0,<1.99.99',
        'unplugged>=0.1.6,<0.1.99',
        'imdbparser>=1.0.20,<1.99.99',
        'malparser>=1.1.7,<1.99.99',
        'thomas>=2.2.3,<2.99.99',
        'timeoutthreadpoolexecutor>=1.0.2,<1.0.99',
        'certifi',
        'pillow',
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
