# syncacre
Syncacre is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges and especially as clients. Consequently they can operate from behind restrictive firewalls.

All what Syncacre needs is an external storage space such as an SSH or WebDAV account on a server. The nodes running Syncacre can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.

