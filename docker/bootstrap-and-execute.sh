#!/usr/bin/env bash

cd /tridentstream

# install additional plugins
if [ ! -e "requirements.txt" ]; then
    touch "requirements.txt"
fi
pip install -r requirements.txt

# install plugins
shopt -s nullglob
if [ -d "packages" ]; then
    for filename in packages/*.{tar.gz,zip,whl}; do
        pip install "$filename"
    done
fi

# initialize tridentstream
bootstrap-tridentstream

# load extra fixtures
if [ -d "fixtures" ]; then
    for filename in fixtures/*.json; do
        python manage.py loaddata "$filename" && mv "$filename" "$filename.loaded"
    done
fi

# remove any potential pid
rm /twistd.pid

# start up with server description
if [ "$SERVER_DESCRIPTION" != "" ]
then
    twistd -n --pidfile=/twistd.pid tridentstream -s -e "$SERVER_DESCRIPTION" $@
else
    twistd -n --pidfile=/twistd.pid tridentstream -s $@
fi
