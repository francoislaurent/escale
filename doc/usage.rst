
General usage
=============


Command-line
------------

escale
^^^^^^

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
^^^^^^^^^

This command makes it easier to start and stop |escale|:

.. parsed-literal::

        escalectl start
        escalectl stop


Access modifier edition
"""""""""""""""""""""""

It also permits to set access modifiers for individual files:

.. parsed-literal::

        escalectl access <filename> <modifiers>

where ``<modifiers>`` is any contiguous combination of access modifiers.

An access modifier begins with either ``r`` for read or ``w`` for write and may end with any of ``+`` (allowed, default), ``-`` (forbidden) or ``?`` to unset the existing modifier if any.

Without ``<modifiers>``, ``escalectl access <filename>`` shows the modifiers for file ``<filename>``.

See command-line help for more information:

.. parsed-literal::

        escalectl access --help


Moving relays
"""""""""""""

|escalectl| can also migrate a relay repository from a host and another.

.. parsed-literal::

        escalectl migrate -r <repository> <destination-relay>

where ``<repository>`` is an existing section in the default configuration file 
(optional if you maintain a single repository in |escale|)
and ``<destination-relay>`` is a relay address in the same format as requested during assisted
configuration with *escale -i*.

A relay address for example can be ``<protocol>://<servername>/<path-to-repository>``.

A new configuration file can also be provided instead. 
Beware that section names should match.

More options are listed in:

.. parsed-literal::

        escalectl migrate --help


Backup
""""""

|escalectl| also features repository backup and restoration. 
For example:

.. parsed-literal::

	# back-up the 'my-repository' repository into a 'my-backup.tar.bz2' archive
	escalectl backup my-repository my-backup.tar.bz2 --fast
	# restore the 'my-repository' repository from the 'my-backup.tar.bz2' archive
	escalectl restore my-repository my-backup.tar.bz2 --fast

The ``--fast`` option is recommended only if the repository will not undergo changes during backup or restoration.

Even if called with this option, the process may take a while.
You are advised to copy yourself the remote repository with a native client (FTP, web, etc).


Recovery procedure
""""""""""""""""""

There is a mechanism to recover a lost relay repository, 
provided that all the clients were up-to-date.

.. note:: restrictions may apply if clients run in `conservative` mode.

|escalectl| can restore the placeholders with the ``fix`` subcommand:

.. parsed-literal::

	escalectl fix

A specific repository can be specified if several repositories are defined in the default configuration file.



Configuration file
------------------

A configuration file is a text file with ``key = value`` and ``[section]`` lines.

The ``key = value`` lines that appear before the first ``[section]`` line define global parameters that will be common to all the clients.

Each section refers to a client. It begins with a ``[section]`` where ``section`` can be replaced by the name that will appear in the logs. Each client should have a distinct name.

Parameters that can only be global are:

* ``log file``: path to log file
* ``log rotate``: number of rotated log files (default: 3)

.. note:: booleans can be either ``yes``, ``no``, ``1``, ``0``, ``true``, ``false``, ``on`` or ``off``.

.. note:: regular expressions for filenames can be basic strings with wildcard ``*`` as the only supported metacharacter, or full regular expressions as recognized by the `re` module if they begin and (optionally) end with the ``/`` character.

Other parameters are:

* ``local path`` (or ``path``): path to the local repository
* ``protocol``: either ``ftp``, ``ftps``, ``webdav``, ``http``, ``https``, ``file``, ``rclone``, ``dropbox``, ``googlecloud``, ``googledrive``, ``amazoncloud``, ``s3``, ``onedrive``, ``b2``, ``hubic``, ``sftp`` or ``swift``. See `Relay backends`_
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
* ``include`` (or ``include files``, ``pattern``, ``filter``): comma-separated list of regular expressions to filter in files by name
* ``exclude`` (or ``exclude files``): comma-separated list of regular expressions to filter out files by name
* ``include directories`` (or ``include directory``): comma-separated list of regular expressions to filter in directories by relative path; works properly only on top directories
* ``exclude directories`` (or ``exclude directory``): comma-separated list of regular expressions to filter out directories by relative path
* ``disk quota``: a decimal number with storage space units such as ``KB``, ``MB``, ``GB``, etc
* ``maintainer``: an email address; if a client aborts and an SMTP server is available on the client machine, a notice email can be sent to this address
* ``mode`` (or ``synchronization mode``): either ``download`` (synonym of ``pull only = yes``), ``upload`` (synonym of ``push only = yes``), ``conservative``/``preservative`` or ``share``/``shared`` (default). See `Synchronization modes`_
* ``lock timeout``: timeout for unclaimed locks, in seconds
* ``puller count`` (or ``pullers``): number of puller nodes operating on the remote repository. See `Multi-client and multi-puller regimes`_
* ``checksum`` (or ``hash algorithm``): boolean (default: true) or hash algorithm has supported by :func:`hashlib.new`. See also `hashlib.algorithms_available`
* ``checksum cache``: boolean (default: True) for whether to make the local checksum cache persistent
* ``index`` (or ``compact``): boolean (default: false) or string; index-based relay repository management; see also `Indexing`_
* ``maxpagesize`` (or ``maxarchivesize``): a decimal number with optional storage space units such as ``KB``, ``MB``, ``GB``, etc (default value: 1 GB, default unit: MB)
* ``priority``: admits only ``upload`` as a value; see also `Synchronization modes`_


Relay backends
--------------

|escale| features FTP (``ftp``, ``ftps``) and WebDAV (``http``, ``https``, ``webdav``) native clients. 

It relies on `rclone`_ (``rclone``) for Dropbox, Google Cloud Storage, Google Drive, Amazon Cloud Storage, Amazon S3, Microsoft OneDrive and others. 

There is also Google Drive client (``googledrive``) that requires the `drive`_ utility. 

This is governed by the ``protocol`` configuration option.

In addition, a local directory (or mount; ``file``) can be used as a relay repository. 

This is especially useful when no native client is available for a given service but third party software can mount the remote space into the file system.

For example Dropbox is not yet natively supported by |escale| but the Dropbox proprietary client can synchronize a directory and |escale| can use this or any synchronized subdirectory.

In the case of Dropbox, however, using ``protocol = rclone`` instead or equivalently ``protocol = dropbox`` is recommended.


Synchronization modes
---------------------

The synchronization mode can be ``upload``, ``download``, ``shared`` or ``conservative``:

* ``upload``: local files are sent to the other clients; 
  local files cannot be modified.

* ``download``: all new files or file modifications from other clients are admitted;
  local files are not be sent over the internet but can be modified.

* ``shared``: files are fully synchronized; all file additions and modifications are propagated
  and local files can be modified.

* ``conservative``: local files are sent to the relay repository but cannot be overwritten
  except if they originate from another client and have never been locally modified.

A one-way transfer link will typically define a client running in 'upload' mode and others running in 'download' mode.

Full synchronization of two clients will be achieved setting both clients to run in 'shared' mode.

The ``shared`` and ``conservative`` modes, together with indexing, admit the ``priority = upload`` setting that makes upload take priority over download.
When many files are available for upload when an upload round begins, the client sends as many updates as necessary to upload all these files. 
This excludes the files that are newly added during the upload round.

Letting upload take priority may be especially helpful if the local repository happens to be a bottleneck,
for example repositories with millions of files available on an NFS mount.

This option is not recommended though. 
This may lead to a deadlock if an update from another client is available on the relay.
It is recommended instead to set two separate clients, one in ``download`` mode and the other in ``upload`` mode.


Multi-client and multi-puller regimes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For now, multi-client/multi-puller scenarios may lead to conflicts or inconsistensies in the local and remote repositories.

Use it at your own risk.

.. todo:: make doc


Encryption
----------

Two encryption algorithms are supported: ``fernet`` from the `cryptography`_ library and ``blowfish``. 

Some backends also support ``native`` when the proper backend features an encryption mechanism.
See for example the ``googledrive`` backend.

``blowfish`` has two backends: ``blowfish.cryptography`` from the `cryptography`_ library (default if the library is available) and ``blowfish.blowfish`` from the `blowfish`_ library.

Note that ``blowfish.cryptography`` and ``blowfish.blowfish`` cannot interoperate.

Both algorithms require a passphrase that follow a specific format. It is advised that the first node lets ``escale -i`` generate a passphrase (available in the configuration directory) and then to communicate the generated passphrase to the other nodes.

.. note:: never send credentials or passphrases by plain email. Consider encrypted email or services like `onetimesecret.com <https://onetimesecret.com>`_ instead.


Indexing
--------

The files in a default repository are represented as individual files on the relay.
This is suitable for directory structures with limited number of subdirectories and files.

To synchronize thousands of small files, the indexing alternative is recommended.

It is driven by the ``ìndex`` and ``maxpagesize`` configuration attributes.
``index = 1`` sets indexing on.

A comprehensive index file is made available in the relay repository.
When files are to be transferred, they are bundled into a compressed archive and propagated 
through the relay repository together with a limited index file that lists the content of the archive.

The archive is compressed (and encrypted if encryption is on) once the total size of the pending files reaches the value defined by the ``maxpagesize`` configuration parameter, or no more files are to be sent.

Note that compression makes the actual uploaded data smaller than the ``maxpagesize`` value. 
One may increase this latter value at the risk of an update exceeding the maximum size.
Note that some relay services may not explicitly reject an oversized files and replace the expected data file by a zero-byte file instead.
This may happen again and again until the upload content results in a small-enough file.

See also the `protocol <protocol.html>`_ section.


.. |escalecmd| replace:: *escale*
.. |escalectl| replace:: *escalectl*

