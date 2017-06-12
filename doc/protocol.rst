
Communication protocol
----------------------

This section describes the general communication logic between the nodes that operate on a common relay repository.

The scheme described below applies to all the current backends that derivate from the |relay| class.

A |example-file| file, when uploaded to the relay repository, is accompanied by two hidden files: |example-lock| and |example-placeholder|.

Note that the '*.*' prefix and '*.lock*' and '*.placeholder*' suffixes are defined in the |relay| class.
A valid backend does not need to handle locks and placholders as individual files. 
It should instead implement the more general :class:`~escale.relay.relay.AbstractRelay` interface.

Lock files
~~~~~~~~~~

|example-lock| is written at the beginning of any transfer (upload or download) and deleted once the transfer is completed. 
When a lock file is associated to a regular file, only the owner of the lock can operate on the file.

A lock file contains the name of the owner client and the type of operation ('*mode: w*' for uploads, '*mode: r*' for downloads).

When a client fails during such an operation, it can later undo the commited modifications. 
See also the `Recovery from failure`_ section.

In earlier versions, lock files did not contain any information, hence the concept of unclaimed locks. 
Unclaimed locks can be deleted by any client after some time has passed. 
The |relay| class features a `lock_timeout` attribute. 
However this is not relevant with versions starting even before `0.5` (first version released and promoted outside github).

Placeholder files
~~~~~~~~~~~~~~~~~

Placeholder files are the most persistent files. 
They stay forever in the relay repository. 
They can be deleted under specific circumstances to request the corresponding regular file again.

In earlier versions, they were created once the corresponding regular file was deleted, hence the *placeholder* suffix.

However they now contain meta information such as the last modified time of the corresponding regular file. 
As a consequence, they are now created at upload time and already exist when the corresponding regular file is available in the relay repository.

Each time a puller client gets a copy of the file, it marks the file as read by registering itself in the placeholder file. 
This mechanism helps determining when a file can be deleted in a multi-puller setting.

Message files
~~~~~~~~~~~~~

.. note:: This feature is not yet implemented. It is exposed here as a support for discussion about inter-client communication in multi-puller settings.

Message files exist only in multi-puller settings.

These files can be created when the relay storage space is full. 
Regular files that were pulled at least once can be deleted by a pusher that needs to upload more files, and each deleted regular file is replaced by a message file. 
They are actual placeholders, but temporary ones.

The pullers that didn't get their copy of a deleted regular file are "notified" by the existence of such message files. 
As a consequence they can request the regular file again.

This mechanism is supposed to overcome the problem of puller downtime. 
Indeed, in multi-puller settings, regular files are cleared from the relay repository by the last puller, i.e. once all pullers got their respective copy of the regular file. 
When a puller node gets down, the files that this client didn't download would stay in the relay repository as long as this client is down.

Message filenames are in the form |example-message|. 
They have a *message* extension and may have a subextension that remains to be defined (will probably be a timestamp).

The subextension should change on any modification of the content of the message file. 
This permits to let the other clients know when the message file should be read again.

Indeed, the clients should read all the new message files each time they crawl the repository in search for changes. 
The clients should locally cache these message files to avoid multiple downloads. 
It is assumed here that every transfer is costly (e.g. API cost) and should be avoided if possible.

The subextension can be omitted by relays that have access to last modified time of message files.

Recovery from failure
~~~~~~~~~~~~~~~~~~~~~

.. todo:: make doc

Multi-puller scenarios
~~~~~~~~~~~~~~~~~~~~~~

.. todo:: make doc


.. |example-file| replace:: *my-file*
.. |example-lock| replace:: *.my-file.lock*
.. |example-placeholder| replace:: *.my-file.placeholder*
.. |example-message| replace:: *.my-file.<hash>.message*
.. |relay| replace:: :class:`~escale.relay.relay.Relay`
