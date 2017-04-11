.. SynCÀCRe documentation master file, adapted from a file created by
   sphinx-quickstart on Tue Jan 24 11:46:04 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SynCÀCRe documentation
======================

|syncacre| is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what |syncacre| needs is an external storage space such as an SSH or WebDAV account on a server. The nodes running |syncacre| can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.


Installation
------------

You will need Python >= 2.7 or >= 3.5.
::

	git clone https://github.com/francoislaurent/syncacre.git
	cd syncacre
	pip install --user -e .

The ``-e`` option is necessary if you intend to update or modify the code and have the modifications reflected in your installed |syncacre|.

To compile the documentation and get a local copy, after installing |syncacre| do:
::

	cd doc
	make html

The generated documentation will be available at ``_build/html/index.html`` from the ``doc`` repository.


Commandline
-----------
::

	> python -m syncacre -c <path-to-conf-file>

You can run |syncacre| as a daemon (in background) with:
::

	> python -m syncacre -d -c <path-to-conf-file>

If no configuration file is provided on the commandline, |syncacre| will look for one of the following files: ``/etc/syncacre.conf`` (system-wide), ``~/.syncacre/syncacre.conf``, ``~/.config/syncacre/syncacre.conf`` where ``~`` stands for the home directory.


Configuration file
------------------

A configuration file is a text file with ``key = value`` and ``[section]`` lines.

The ``key = value`` lines that appear before the first ``[section]`` line define global parameters that will be common to all the clients.

Each section refers to a client. It begins with a ``[section]`` where ``section`` can be replaced by the name that will appear in the logs. Each client should have a distinct name.

Parameters that can only be global are:

* ``log file``: path to log file
* ``daemon``: boolean

.. note:: booleans can be either ``yes``, ``no``, ``1``, ``0``, ``true``, ``false``, ``on`` or ``off``.

Other parameters are:

* ``local path`` (or ``path``): path to the local repository
* ``remote address`` (or ``host address``, ``relay address``, ``address``): address of the remote host
* ``remote directory`` (or ... + ``dir`` variants): directory of the repository on the remote host
* ``username``: username on the remote host
* ``password`` or ``secret file`` or ``credential``: password on the remote host or path to a file that contains the password or both the username and the password on a single line (``username:password``)
* ``refresh``: synchronization interval in seconds
* ``modification time`` or ``mtime`` or ``timestamp``: see :class:`~syncacre.manager.Manager`.
* either ``write only`` or ``read only``: boolean that defines whether the client should only push (read only) or pull (write only). By default a client both pushes and pulls
* ``encryption``: boolean that defines whether to encrypt/decrypt the files or not
* ``passphrase`` or ``key``: passphrase or path to a file that contains the passphrase for the encryption algorithm

.. note:: the ``conf`` and ``test`` directories contain examples of configuration files.


API
---

.. toctree::
   :maxdepth: 1

   log
   relay
   manager
   encryption

.. Indices and tables
.. ------------------

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

.. |syncacre| replace:: **Syncacre**

