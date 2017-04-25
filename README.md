# Syncacre

Syncacre is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what Syncacre needs is an external storage space such as an FTP or WebDAV account on a server. The nodes running Syncacre can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.


## Documentation

Find the extended documentation at [syncacre.readthedocs.io](http://syncacre.readthedocs.io/en/latest/).


## Changelog:

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

Current version is `0.3.1`.

Coming features are:

* FTP support
* resume interrupted upload/download
* improved temporary file management (no orphan files)
* improved lock management (no orphan files)
* file auto-destruction when several pullers have been defined and one takes too much time to get its copy of the file
* actually support multiple pullers using the configuration file (for now only the library can)
* more (symmetric) cryptographic algorithms and more cryptographic options

Previously advertised coming features that may be abandoned:

* SSH support; see [issue #3](https://github.com/francoislaurent/syncacre/issues/3)


## Alternative solutions

If you can get a F\*EX account, you may find [the F\*EX service](http://fex.rus.uni-stuttgart.de/) more convenient.

Extra tools include [Stream EXchange](http://fex.belwue.de/SEX.html).

A [F\*EX use case](http://fex.rus.uni-stuttgart.de/usecases/fexpush.html) will actually be considered for integration into Syncacre.

