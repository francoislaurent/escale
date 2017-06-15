# Escale

*Escale* (French: stop, halt, stopover) synchronizes files between clients that operate behind restrictive firewalls.

It makes use of common file transfer solutions (FTP) and popular cloud solutions such as Dropbox, Google Drive and WebDAV servers including Yandex Disk.

*Escale* maintains a relay repository in a folder inside the remote or cloud storage space and frees memory as soon as copies of the shared files have been propagated to all the clients.
File modifications are also propagated.

It features end-to-end encryption, quota management, filename filters, access control and adaptive transmission latencies. 
It also features useful management routines such as migration, backup and restoration of relay repositories.

It can run as a daemon and simultaneously synchronize several repositories between multiple clients.


## License

*Escale* is governed by the [CeCILL-C](http://cecill.info/licences/Licence_CeCILL-C_V1-en.html) license.

It derivates from a work called *Syncacre* distributed under the terms of the ISC license. See release 0.4.3 for a copy of that former work.


## Documentation

Please find the extended documentation at [escale.readthedocs.io](http://escale.readthedocs.io/en/latest/).


## Changelog:

* `0.5` (including `0.5-rc*`):

  * project name becomes *Escale*
  * license becomes [CeCILL-C](http://cecill.info/licences/Licence_CeCILL-C_V1-en.html)
  * license acceptance requested on the command-line
  * the `syncacre` script is renamed `escale`
  * `escalectl` script
  * access permissions (read, write, no read, no write) for individual files
  * ``mode`` configuration option
  * ``conservative`` synchronization mode
  * persistent data may be stored in the configuration directory
  * migration of relay repositories from a host to another
  * backup relay repositories to an archive
  * restore relay repositories from an archive
  * when missing, the ``client`` configuration option is set to the local hostname
  * unclaimed locks can be cleared by any client after ``lock timeout``
  * ``lock timeout`` configuration option
  * ``puller count``/``pullers`` configuration option
  * if *puller count* is ``1``, regular files on the relay space are auto-deleted if the puller's local copies are up-to-date
  * ``include``/``include files`` as synonyms for ``filter``
  * ``exclude``/``exclude files`` configuration option
  * relay backend for directories in the local file system; the ``protocol`` configuration option admits value ``file``
  * relay backend for Google Drive; the ``protocol`` configuration option admits value ``google`` and ``googledrive``
  * the ``encryption`` configuration option admits value ``native`` for ``google``/``googledrive`` repositories
  * ``-q`` command-line option deprecated
  * [python-daemon](https://pypi.python.org/pypi/python-daemon/) becomes a non-optional dependency
  * the documentation can be compiled by the Python2 version of Sphinx
  * documentation extensively redesigned
  * various bugfixes

* `0.4.3`:

  * various bugfixes
  * `syncacre` script

* `0.4.2`:

  * new lock format with version and access mode information
  * auto-repair for uncomplete transfers
  * ``pattern``/``filter`` configuration option to filter filenames by regular expression
  * ``-r`` command-line option for auto-restart when unrecoverable errors are hit

* `0.4.1`:

  * ask for username and password at runtime
  * FTP backend now supports vsftpd and proftpd, MLSD-deficient FTP servers and FTP TLS connections
  * ``disk quota`` configuration option
  * ``certificate``, ``certfile`` and ``keyfile`` configuration options
  * ``maintainer`` configuration option
  * email the maintainer when a client is aborting, if the local machine hosts an SMTP server

* `0.4`:

  * FTP support (tested with pure-ftpd)
  * unicode support
  * ``-i`` command-line option that assists the user in configuring Syncacre
  * ``-p`` command-line option deprecated
  * if ``refresh`` configuration option is missing, defaults to ``True``
  * most exceptions no longer make syncacre abort
  * temporary files are properly cleared

* `0.3.2`:

  * ``file extension`` filter in configuration file
  * multiple backends for blowfish encryption; backend can be enforced with ``encryption = algorithm.backend`` where ``algorithm`` is ``blowfish`` here and ``backend`` can be either ``blowfish`` or ``cryptography``
  * file names are correctly escaped
  * sleep times increase with successive sleeps

* `0.3.1`:

  * ``push only`` and ``pull only`` configuration options introduced as replacements for 
    ``read only`` and ``write only``
  * ``ssl version`` and ``verify ssl`` configuration options


## Roadmap

Coming features are:

* resume interrupted upload/download
* file auto-destruction when several pullers have been defined and one takes too much time to get its copy of the file
* actually support multiple pullers (not tested yet)
* split and recombine big files
* more (symmetric) cryptographic algorithms and more cryptographic options
* rclone-based generic backend
* SSH backend
* google-api-python-client backend for Google Drive
* F\*EX/SEX backend?
* configuration wizard with explicit switch of commercial services

