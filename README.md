# Syncacre

Syncacre is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what Syncacre needs is an external storage space such as an account on a FTP or WebDAV server. The nodes running Syncacre can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.


## Documentation

Find the extended documentation at [syncacre.readthedocs.io](http://syncacre.readthedocs.io/en/latest/).


## Changelog:

* `0.4.1`:

  * ask for username and password at runtime
  * FTP backend now supports vsftpd, MLSD-deficient FTP servers and FTP TLS connections
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
* auto-clear locks on restart
* file auto-destruction when several pullers have been defined and one takes too much time to get its copy of the file
* actually support multiple pullers
* split and recombine big files
* more (symmetric) cryptographic algorithms and more cryptographic options
* OAuth support
* SSH support


## Alternative solutions

If you can get a F\*EX account, you may find [the F\*EX service](http://fex.rus.uni-stuttgart.de/) more convenient.

Extra tools include [Stream EXchange](http://fex.belwue.de/SEX.html).

A [F\*EX use case](http://fex.rus.uni-stuttgart.de/usecases/fexpush.html) will actually be considered for integration into Syncacre.

