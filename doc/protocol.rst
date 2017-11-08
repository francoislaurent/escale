
Communication protocol
----------------------

This section describes the general communication logic between the nodes that operate on a common relay repository.

The scheme described below applies to all the current backends that derivate from the |relay| class, except for *local file* and *FTP* relays.

.. note:: The current (index-based) scheme was introduced with version *0.7*. The former scheme is still maintained and documented `here <placeholders.html>`_.

The relay repository consists primarily of an index file.
This index file contains meta information for files that were or are transferred.
This primary index will be referred to as the persistent index.

When new files or modified versions of files are to be sent to the relay, they are bundled together into a compressed archive (*.tar.bz2*).

The archive is accompanied by an index similar to the persistent index, but limited to specifying the content of the archive.

The archive and attached index form together an update, and they will be referred to as update data and update index respectively.

In addition, the indexing mechanism supports paging, i.e. the total repository can be split down into several pages and each page consists of a persistent index and optionaly an update.
By default, `escale` maintains a single page, but multi-paging could easily be introduced by overwriting the :meth:`~relay.index.IndexRelay.page` and :meth:`~relay.index.IndexRelay.allPages` methods of the :class:`~relay.index.IndexRelay` class.

An example of multi-page indexing can be found in the :class:`~relay.index.TopDirectoriesIndex` class.
This class is used as a relay if ``index = topdir``.
It maintains as many pages as there are top directories in the repository, plus a default "0" page for files that are not in these directories.
In addition, this class can manage several levels of directories.
For example, if ``index = topdir:2``, a distinct page will be maintained for each "A/B" sub-directory, where "A" is a top directory and "B" a sub-directory in "A".

For each page, no more than a single update can be available for download on the relay.
As a consequence, active clients cannot push a new update as long as the current available update has not been consumed by all the pullers.

When a non-trivial read or write operation is to be performed on the relay, the client locks the page with a lock file.


Lock files
~~~~~~~~~~

A lock file is written at the beginning of any transfer (upload or download) and deleted once the transfer is completed. 
When a lock file is associated to a regular file, only the owner of the lock can operate on the file.

A lock file contains the name of the owner client and the type of operation ('*mode: w*' for uploads, '*mode: r*' for downloads).

When a client fails during such an operation, it can later undo the commited modifications. 
See also the `Recovery from failure`_ section.


Index files
~~~~~~~~~~~

Index files contain lists of files together with meta information such as the last modified time and checksum of the corresponding regular file.

The persistent index is read by the clients only at startup time. 
Pushers update this index each time they send an update.

Update indices are duplicate information. 
Their purpose is to make the pullers generate less traffic.
Indeed pullers only need update indices.

Each time a puller client gets a copy of an update, it marks the update as read/consumed by registering itself in the update index. 
As a consequence pullers overwrite the update index on the relay.
This mechanism helps determining when an update can be deleted from the relay in a multi-puller setting.


Recovery from failure
~~~~~~~~~~~~~~~~~~~~~

On restart, a client may find a page lock that it is supposed to own.
In this situation, depending on whether the failed transaction was a read or a write, the client tries to fix the state of the page before releasing the lock.

Another misbehaviour can be detected when a puller client cannot find local copies of files that are referenced in the relay index.
In this situation, the client updates the persistent index after removing the entries corresponding to the missing files.
The pusher clients check whether the persistent index has been modified based on the last modified time of the file on the relay and downloads it if modified.


Multi-puller scenarios
~~~~~~~~~~~~~~~~~~~~~~

.. todo:: make doc


.. |relay| replace:: :class:`~escale.relay.relay.Relay`
