Escale documentation
====================

     
|escale| (French: stop, halt, stopover) synchronizes files between clients that operate behind restrictive firewalls.

It makes use of common file transfer solutions (FTP) and popular cloud solutions such as Dropbox, Google Drive and WebDAV servers including Yandex Disk.

|escale| maintains a relay repository in a folder inside the remote or cloud storage space and frees memory as soon as copies of a shared file have been propagated to all the clients. File modifications are also propagated.

It features end-to-end encryption, quota management, filename filters, access control and adaptive transmission latencies. 
It also features useful management routines such as migration, backup and restoration of relay repositories.

It can run as a daemon and simultaneously synchronize several repositories between multiple clients.


|escale|'s project page is on `github.com <https://github.com/francoislaurent/escale>`_.


.. .. centered:: `[fr] <index.fr.html>`_ `[ру] <index.ru.html>`_


User guide
----------

.. toctree::
   :maxdepth: 2

   terms
   install
   usage
   howtos


Developer guide
---------------

.. toctree::
   :maxdepth: 2

   terms
   dependencies
   protocol
   persistency
   api


.. In other languages
.. ------------------

.. .. toctree::
..    :maxdepth: 1

.. .  [fr] <index.fr>
.. .  [ру] <index.ru>


.. Indices and tables
.. ------------------

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

.. |escale| replace:: **Escale**

