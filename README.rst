================================
Tridentstream Media Server
================================

Stream everything...

.. contents::


WARNING! ALPHA SOFTWARE
--------------------------------

Tridentstream is currently alpha-software and this means stuff is broken and stupid.
It also means that any plugin you make or use can break with any given update.

Feel free to report bugs and potentially missing features so we can move the whole project into beta.
You can also take this chance to move the whole project in a direction you like.

Due to the Alpha status (unstable interfaces between plugins internally) the tests are quite sparse. So things broken might not be caught automatically.

The Alpha status includes the documentation that might be lacking or completely missing regarding certain aspects.


Requirements
--------------------------------

* Only tested on Linux
* Python 3.6 or 3.7

Optional Requirements

* `Organized data <UNORGANIZED-DOCS.rst#organizing-data>`__
* `Friends with organized data <UNORGANIZED-DOCS.rst#sharing-data>`__
* `Other external data-sources <UNORGANIZED-DOCS.rst#-searchers>`__


Installation guides
--------------------------------

Get this party going with a basic setup

With docker and docker-compose
````````````````````````````````

Requirements

* A server with root access (Ubuntu or Debian for this guide).
* A domain already pointing towards the server.

If you do not already have docker and docker-compose installed, do this:

.. code-block:: bash

    apt-get install \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg-agent \
        software-properties-common -y
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable"
    apt-get install docker-ce docker-ce-cli containerd.io -y
    curl -L "https://github.com/docker/compose/releases/download/1.25.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose


To get started, clone the setups repository

.. code-block:: bash

    git clone https://github.com/tridentstream/setups

Head into the linux-docker folder

.. code-block:: bash

    cd setups/linux-docker

OPTIONAL: If you do not have your own webserver to be infront of the Tridentstream instance, then traefik is recommended.
It's easy to get going and is already included.

.. code-block:: bash

    docker network create web
    cd traefik
    touch acme.json
    chmod 600 acme.json
    docker-compose up -d
    cd ..

Time to get Tridentstream bootstrapped.

.. code-block:: bash

    # If you do not need to use built-in deluge, skip -d
    ./bootstrap.sh -d -o your-domain.com

Follow the on-screen instructions and read the `Setting Up`_ section.

Please note, if you do not use traefik as prescribed, then you will need to modify docker-compose.yml to fit your needs.

To install plugins, put the plugin installation package into tridentstream/packages, edit .env and add its name to INSTALLED_APPS.


Setting Up
--------------------------------

First time you login, a user is created with the info you logged in with. That is an administrative user.

After you logged in, head over to the Admin page, click "Plugins".

The first plugin type you want to add is a new data source, that's the plugins on the right of the page.
This can be one from local or remote data, or it can be sourced from website you have access to (i.e. a searcher).

Find one in the list that fits your need and add it. Then add a Section or a Store that works with your input.

After you have finished changing a "Sections" or "Store", remember to "Commit changes"


External Players
---------------------------------

Tridentstream Media Server does not really play anything by itself but can interact with some external players.

Under "Features", "full" means that it supports complete remote control and tracking through Tridentstream Media Server,
i.e. you can pause and play and it reports back how much you have watched of a given media item.


.. list-table:: Player support
   :header-rows: 1

   * - Name
     - Playback tracking
     - Sections access
     - Store access
     - Relation
     - Note
     - Link
   * - Kodi plugin
     - Yes
     - Yes
     - No
     - First-party
     -
     - `Link <https://kodi.tridenstream.org>`__
   * - StreamProtocol
     - No
     - N/a
     - N/a
     - First-party
     - Only Windows for now
     - `Link <https://streamprotocol.tridenstream.org>`__


License
---------------------------------

MIT