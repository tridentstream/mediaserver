================================
Tridentstream Media Server
================================

Stream everything...

.. contents::


WARNING! ALPHA SOFTWARE
--------------------------------

Tridentstream is currently alpha software and this means stuff is broken and things change.
It also means that any plugin you make or use can break with any given update.

Feel free to report bugs and potentially missing features so we can move the whole project into beta.
You can also take this chance to move the whole project in a direction you like.

Due to the Alpha status (unstable interfaces between plugins internally) the tests are quite sparse. So things broken might not be caught automatically.

The Alpha status includes the documentation that might be severely lacking or completely missing regarding certain aspects.


Requirements
--------------------------------

* Only tested on Linux
* Python 3.7 or higher

Optional Requirements

* `Organized data <UNORGANIZED-DOCS.rst#organizing-data>`__
* `Friends with organized data <UNORGANIZED-DOCS.rst#sharing-data>`__
* `Other external data-sources <UNORGANIZED-DOCS.rst#-searchers>`__


Installation guides
--------------------------------

Get this party going with a basic setup,
`check out the ways to install in the setups repostiory <https://github.com/tridentstream/setups>`__


Setting Up
--------------------------------

First time you login, a user is created with the info you logged in with. That is an administrative user.

After you logged in, head over to the Admin page, click "Plugins".

The first plugin type you want to add is a new data source, that's the plugins on the right side of the page.
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