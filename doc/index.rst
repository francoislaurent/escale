SynCÀCRe documentation
======================

|syncacre| is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what |syncacre| needs is an external storage space such as an account on a FTP or WebDAV server. The nodes running |syncacre| can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.

|syncacre|'s project page is on `github.com <https://github.com/francoislaurent/syncacre>`_.


Installation
------------

You will need Python >= 2.7 or >= 3.5.
::

	git clone https://github.com/francoislaurent/syncacre.git
	cd syncacre
	pip install --user -e .

The ``-e`` option is necessary if you intend to update or modify the code and have the modifications reflected in your installed |syncacre|.

.. note:: never run |syncacre| as the super user. |syncacre| does not need any special privilege.

If you wish to compile the documentation and get a local copy of it, you will need Sphinx for Python3.
Once |syncacre| is installed, type:
::

	cd doc
	make html

The generated documentation will be available at ``_build/html/index.html`` from the ``doc`` repository.


Commandline
-----------
The simplest way to call |syncacre| is:
::

	python -m syncacre

This, however, will fail the first time you run |syncacre|, because you need to configure it first with the ``-i`` option:
::

	python -m syncacre -i

You can alternatively select a specific conf file with the ``-c`` option:
::

	python -m syncacre -c <path-to-conf-file>

Last but not least, you can run |syncacre| as a daemon (in background) with the ``-d`` option:
::

	python -m syncacre -d

If no configuration file is provided on the commandline, |syncacre| will look for one of the following files: ``/etc/syncacre.conf`` (system-wide), ``~/.syncacre/syncacre.conf``, ``~/.config/syncacre/syncacre.conf`` where ``~`` stands for the home directory.


Configuration file
------------------

A configuration file is a text file with ``key = value`` and ``[section]`` lines.

The ``key = value`` lines that appear before the first ``[section]`` line define global parameters that will be common to all the clients.

Each section refers to a client. It begins with a ``[section]`` where ``section`` can be replaced by the name that will appear in the logs. Each client should have a distinct name.

Parameters that can only be global are:

* ``log file``: path to log file

.. note:: booleans can be either ``yes``, ``no``, ``1``, ``0``, ``true``, ``false``, ``on`` or ``off``.

Other parameters are:

* ``local path`` (or ``path``): path to the local repository
* ``host address`` (or ``relay address``, ``remote address``, ``address``): address of the remote host
* ``host directory`` (or ... + ``dir`` variants): directory of the repository on the remote host
* ``username``: username on the remote host
* ``password`` or ``secret file`` or ``credential``: password on the remote host or path to a file that contains the password or both the username and the password on a single line (``username:password``)
* ``refresh``: synchronization interval in seconds
* ``modification time`` or ``mtime`` or ``timestamp``: see :class:`~syncacre.manager.Manager`
* either ``push only`` or ``pull only``: boolean that defines whether the client should only push or pull. By default a client both pushes and pulls. Supported aliases for ``push only`` and ``pull only`` are ``read only`` and ``write only`` respectively
* ``encryption``: boolean that defines whether to encrypt/decrypt the files or not, or algorithm identifier (e.g. ``fernet``, ``blowfish``, etc)
* ``passphrase`` or ``key``: passphrase or path to a file that contains the passphrase for the encryption algorithm
* ``certificate`` or ``certfile``: path to the client certificate
* ``keyfile``: path to the client private key
* ``verify ssl``: boolean that defines whether to check the remote host's certificate
* ``ssl version``: either ``SSLv2``, ``SSLv3``, ``SSLv23``, ``TLS``, ``TLSv1``, ``TLSv1.1`` or ``TLSv1.2``
* ``file extension`` (or ``file type``): a comma-separated list of file extensions (with or without the initial dot)
* ``disk quota``: a decimal number with storage space units such as ``KB``, ``MB``, ``GB``, etc
* ``maintainer``: an email address; if a client aborts and an SMTP server is available on the client machine, a notice email can be sent to this address


API
---

.. toctree::
   :maxdepth: 1

   cli
   log
   base
   relay
   manager
   encryption

.. Indices and tables
.. ------------------

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

.. |syncacre| replace:: **Syncacre**

