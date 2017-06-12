
General usage
=============


Command-line
------------

escale
~~~~~~

The simplest way to run |escale| is to type:
::

	escale

This, however, will fail the first time you run |escale|, because you need to configure it first with the ``-i`` option:
::

	escale -i

You can alternatively select a specific conf file with the ``-c`` option:
::

	escale -c <path-to-conf-file>

Last but not least, you can run |escale| as a daemon (in background) with the ``-d`` option:
::

	escale -d

If you run |escale| as a daemon or with multiple clients (as defined in the configuration file), you may find it more convenient to start and stop |escale| with the `escalectl`_ command.

.. note:: never run |escale| as the super user. |escale| does not need any special privilege.

If no configuration file is provided on the commandline, |escale| will look for one of the following files: */etc/escale.conf* (system-wide), *~/.escale/escale.conf*, *~/.config/escale/escale.conf* where *~* stands for the home directory.


escalectl
~~~~~~~~~

This command makes it easier to start and stop |escale|:
::

        escalectl start
        escalectl stop

It also permits to set access modifiers for individual files:
::

        escalectl access <filename> <modifiers>

where ``<modifiers>`` is any contiguous combination of access modifiers.

An access modifier begins with either ``r`` for read or ``w`` for write and may end with any of ``+`` (allowed, default), ``-`` (forbidden) or ``?`` to unset the existing modifier if any.

Without ``<modifiers>``, ``escalectl access <filename>`` shows the modifiers for file ``<filename>``.

See command-line help for more information:
::

        escalectl access --help

|escalectl| can also migrate a relay repository from a host and another.
::

        escalectl migrate <destination-relay>

where ``<destination-relay>`` is a relay address in the same format as requested during assisted
configuration with *escale -i*.
For example, it can be ``<protocol>://<servername>/<path-to-repository>``.

A new configuration file can also be provided instead. 
Beware that section names should match.

More options are listed in:
::

        escalectl migrate --help

|escalectl| also features repository backup and restoration. For example:
::

	# back-up 'my-repository' repository into 'my-backup.tar.bz2' archive
	escalectl backup my-repository my-backup.tar.bz2 --fast
	# restore 'my-repository' repository from 'my-backup.tar.bz2' archive
	escalectl restore my-repository my-backup.tar.bz2 --fast

The ``--fast`` option is recommended only if the repository will not undergo changes during backup or restoration.

Even if called with this option, the process may take a while.
You are advised to copy yourself the remote repository with a native client (FTP, web, etc).

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
* ``protocol``: either ``ftp``, ``ftps``, ``webdav``, ``http``, ``https`` or ``file``. See `Relay backends`_
* ``host address`` (or ``relay address``, ``remote address``, ``address``): address of the remote host
* ``host directory`` (or ... + ``dir`` variants): directory of the repository on the remote host
* ``username``: username on the remote host
* ``password`` or ``secret file`` or ``credential``: password on the remote host or path to a file that contains the password or both the username and the password on a single line (``username:password``)
* ``refresh``: synchronization interval in seconds
* ``modification time`` or ``mtime`` or ``timestamp``: see :class:`~escale.manager.Manager`
* either ``push only`` or ``pull only``: boolean that defines whether the client should only push or pull. By default a client both pushes and pulls. Supported aliases for ``push only`` and ``pull only`` are ``read only`` and ``write only`` respectively
* ``encryption``: boolean that defines whether to encrypt/decrypt the files or not, or algorithm identifier (e.g. ``fernet``, ``blowfish``, etc). See `Encryption`_
* ``passphrase`` or ``key``: passphrase or path to a file that contains the passphrase for the encryption algorithm
* ``certificate`` or ``certfile``: path to the client certificate
* ``keyfile``: path to the client private key
* ``verify ssl``: boolean that defines whether to check the remote host's certificate
* ``ssl version``: either ``SSLv2``, ``SSLv3``, ``SSLv23``, ``TLS``, ``TLSv1``, ``TLSv1.1`` or ``TLSv1.2``
* ``file extension`` (or ``file type``): a comma-separated list of file extensions (with or without the initial dot)
* ``pattern`` or ``filter``: a regular expression to filter file by names
* ``disk quota``: a decimal number with storage space units such as ``KB``, ``MB``, ``GB``, etc
* ``maintainer``: an email address; if a client aborts and an SMTP server is available on the client machine, a notice email can be sent to this address
* ``mode`` (or ``synchronization mode``): either ``download`` (synonym of ``pull only = yes``), ``upload`` (synonym of ``push only = yes``), ``conservative`` or ``share`` (default). See `Synchronization modes`_
* ``lock timeout``: timeout for unclaimed locks, in seconds
* ``puller count`` (or ``pullers``): number of puller nodes operating on the remote repository. See `Multi-client and multi-puller regimes`_


Relay backends
--------------

|escale| features FTP (``ftp``, ``ftps``) and WebDAV (``http``, ``https``, ``webdav``) native clients. 
There is also Google Drive client (``googledrive``) that requires the `drive`_ utility. 
This is governed by the ``protocol`` configuration option.

In addition, a local directory (or mount; ``file``) can be used as a relay repository. 
This is especially useful when no native client is available for a given service but third party software can mount the remote space into the file system.

For example Dropbox is not yet natively supported by |escale| but the Dropbox proprietary client can synchronize a directory and |escale| can use this or any synchronized subdirectory.


Synchronization modes
---------------------

.. todo:: make doc


Multi-client and multi-puller regimes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. todo:: make doc


Encryption
----------

Two encryption algorithm are supported: ``fernet`` from the `cryptography`_ library and ``blowfish``. 
``blowfish`` has two backends: ``blowfish.cryptography`` from the `cryptography`_ library (default if the library is available) and ``blowfish.blowfish`` from the `blowfish`_ library.

Note that ``blowfish.cryptography`` and ``blowfish.blowfish`` cannot interoperate.

Both algorithms require a passphrase that follow a specific format. It is advised that the first node lets ``escale -i`` generate a passphrase (available in the configuration directory) and then to communicate the generated passphrase to the other nodes.

.. note:: never send credentials or passphrases by unencrypted email. Consider services like `onetimesecret.com <https://onetimesecret.com>`_ instead.

.. |escale| replace:: **Escale**
.. |escalecmd| replace:: *escale*
.. |escalectl| replace:: *escalectl*
.. _cryptography: https://cryptography.io/en/latest/
.. _blowfish: https://pypi.python.org/pypi/blowfish/
.. _drive: https://github.com/odeke-em/drive

