FROM python:3.7

ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir -U psycopg2-binary pyopenssl python-memcached leveldb

COPY requirements.txt /
RUN pip install -r /requirements.txt

RUN mkdir /code
COPY setup.py /code/
COPY MANIFEST.in /code/
COPY README.rst /code/
COPY main/ /code/main/
COPY tridentstream/ /code/tridentstream/
COPY twisted/ /code/twisted/

COPY --from=tridentstream/webinterface:latest /dist/ /code/tridentstream/services/webinterface/static/

WORKDIR /code
RUN python setup.py sdist
RUN cp /code/dist/*.tar.gz /
RUN pip install .

WORKDIR /

RUN rm -r /code
RUN mkdir /tridentstream

ADD docker/bootstrap-and-execute.sh /
ADD docker/wait-for-it.sh /

RUN chmod +x /bootstrap-and-execute.sh /wait-for-it.sh

EXPOSE 45477

VOLUME ["/tridentstream"]

CMD ["/bootstrap-and-execute.sh"]
