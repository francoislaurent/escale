# Syncacre

Syncacre is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what Syncacre needs is an external storage space such as an SSH or WebDAV account on a server. The nodes running Syncacre can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.

# Documentation

Find the extended documentation at [syncacre.readthedocs.io](http://syncacre.readthedocs.io/en/latest/).

# Roadmap

Current version is `0.3`.

Coming features are:

	* improved temporary file management (no orphan files)
	* improved lock management (no orphan files)
	* file auto-destruction when several pullers have been defined and one is down
	* SSH support
	* more (symmetric) cryptographic algorithms and more cryptographic options
	* documentation for configuration files

