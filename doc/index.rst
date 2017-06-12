Escale documentation
====================

     
|escale| (French: stop, halt, stopover) is a fault-tolerant client-to-client file synchronization program based on external relay storage.

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what |escale| needs is an external storage space such as an account on a FTP or WebDAV server. The nodes running |escale| can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server once every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.

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

