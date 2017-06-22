
Choosing a relay host
---------------------

|escale| operates with remote file hosting solutions, especially cloud storage solutions.

You may get some storage space that can be programmatically accessed either by one of the native clients provided by |escale| or via a local mount.

These services are usually accessible from behind firewalls because they are operated by external servers.

However these solutions usually require an account at the service provider and this account has be simultaneously accessed by the multiple |escale| instances that your use case necessarily consists of.

Your attention is drawn to the fact that the shared access to a single account may often be prohibited by the terms of use of the corresponding service. It is your responsability to check the compliance of your use case with the terms circulated by your service provider.

|escale| features several native clients. You may instead use an external client provided that this client lets you browse/access your data as a repository mounted in your local file system.

Below follows a list of solutions classified as whether they are or may be supported by a native client, or they can be operated with some external client usually provided by the service provider itself.

The information below may not be up-to-date and is very far from being exhaustive.

+---------------+-----------------+-----------------+------------------+
| Service       | Native support  | Escale backend  | More information |
+===============+=================+=================+==================+
| Box           |    Yes [#nv]_   |     WebDAV      |                  |
+---------------+-----------------+-----------------+------------------+
| Dropbox       |       No        |   LocalMount    | `Dropbox`_       |
+---------------+-----------------+-----------------+------------------+
| Google Drive  |    Yes [#dr]_   |   GoogleDrive   | `Google Drive`_  |
+---------------+-----------------+-----------------+------------------+
| Yandex.Disk   |       Yes       |     WebDAV      | `Yandex.Disk`_   |
+---------------+-----------------+-----------------+------------------+



.. [#nv] not verified
.. [#dr] on top of the `drive`_ utility


.. _Dropbox: Dropbox.html
.. _Google Drive: GoogleDrive.html
.. _Yandex.Disk: YandexDisk.html
