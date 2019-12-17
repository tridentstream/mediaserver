================================
Various information stuff
================================


Getting features used
---------------------------------

There is a lot more to Tridentstream Media Server than just getting it running.

More Launch Options
`````````````````````````````````

There are a bunch of different flags that can be used, run the help command to see them:

.. code-block:: bash

    ../bin/twistd tridentstream --help

An example could be running with debug mode, in foreground and logging to stdout and on a different port:

.. code-block:: bash

    ../bin/twistd tridentstream -d -e tcp:5000 -j -s


Installing New Plugins
`````````````````````````````````

Plugins for Tridentstream Media Server are normally Django Apps with some Tridentstream Plugin System stuff in them.

They can be installed like any normal Python package and loaded in the same way you load any Django App.

Install the plugin
.. code-block:: bash

    ../bin/pip install my-plugin

After you have installed it, check out the plugin README to figure out what the app is called.

In this example, we'll say the README says the app is named `my_plugin`. Open up .env local_settings.py and find `INSTALLED_APPS`.
The result should look something like this

.. code-block:: python

    INSTALLED_APPS=my_plugin,another_plugin

After you restart Tridentstream Media Server you can find your newly installed plugin in the admin interface.

Organizing Data
`````````````````````````````````

Tridentstream Media Server relies on your data being structured with the same hieracy for all of the same type.

By forcing such expectations of the data options are opened for making a different type of plugins
from what other streaming solutions can do. E.g. you won't need to do everything through the filesystem.

So, moving on, how can you structure your data? Any way you want, as long as it's consistent.
There are a few built-in templates for some (hopefully) popular structuring.
The required template structure is in the template description, so you can see it before you add it.

An example could be your TV episodes that can be structured like this: /show.name/season.01/episode.S01E01-stuff.mkv or just /show.name/episode.S01E01-stuff.mkv
It doesn't matter if it is in folders or not, e.g.

    /show.name/episode.S01E01-stuff.mkv
    /show.name/episode.S01E02-stuff/episode.S01E02-stuff.rar

Where the .rar contains the second episode.

Stream Torrents
`````````````````````````````````

There is currently only one supported streaming torrent client, `Deluge-Streaming for Deluge <https://github.com/JohnDoee/deluge-streaming>`_.

So, get Deluge running and install the Deluge-Streaming plugin.

* In the plugin configuration, enable "Allow remote control"
* Add Deluge plugin under "Other plugins"
* Fill in the relevant information and save

You can now use the Torrent client in searchers.

Searchers
`````````````````````````````````

A searcher is a plugin that scrapes an external source, e.g. a website like Youtube.
They turn a website into a format that Tridentstream Media Server can understand.

With searchers you will have an incomplete view of the source you are pulling data from.
This means that it isn't possible to list all Youtube videos but only possible to view a subset through searching.

Sharing Data
`````````````````````````````````

Sharing data with friends and family is both fun and giving. It is also a feature that is front and center in Tridentstream.

It is possible to share local data, others data and even your searchers.
Don't worry, when sharing your searchers the receiving party can only see the names and stream them, no secret information should be leaked.

If you want to share local data, enable them under "Remote filesystems".

If you want to share a searcher, enable them under "Remote searchers".

To allow a user to use the remote searcher, go under Users and give them access to the correct plugin.

Frequently Asked Questions
---------------------------------

What does "Stream" mean in the webinterface.
    The stream option turns media links into links that will be opened directly in your media player.
    This requires a small helper application `that can be found here <http://streamprotocol.tridentstream.org/>`__


The frontpage on the webinterface looks weird / empty / I want it changed.
    I'm not sure what to do exactly about the front page. It can (technically) be customized to do about anything.


How do I trigger a rescan externally?
    Sometimes you might want to trigger rescans automatically, e.g. when a script moved new data into your folder structure.

    This can be done using a command like:
    `curl -H "Authorization: Token <Your Token>" -H "Content-Type: application/json" "https://<Tridentstream Media Server Base URL>/admin/plugins/<Filesystem Plugin ID >/command/" -d '{"command":"rescan","kwargs":{}}'`


Can video be transcoded / subs added / any modifications?
    Not yet, so far there is only a demo project that does this and not a full-blown plugin.
    The problem is that I don't like the models Plex and Jellyfin uses.

    The Plex model seem to require specialized player and the Jellyfin just re-encodes the video to HLS to align keyframes
    (These things might not be true anymore but I doubt they went with the model I like). So I have to make my own.

    If there's a pluggable solution, then do raise an issue.
