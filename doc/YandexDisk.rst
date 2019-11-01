
Yandex.Disk
===========

.. attention:: The native WebDAV client no longer works properly with Yandex.Disk.
   Please favor the rclone backend.
   You may also need to empty the trash from time to time for escale to work smoothly.

|escale| can operate with the Yandex.Disk WebDAV server at webdav.yandex.ru.

.. include:: wizard-part-1.txt

You have to choose a name for the directory that will accommodate the relay repository. 
Here we choose ``Escale Repository`` as a name:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] |enter|
	Request help with '?'
        Address of the relay repository (required): :strong:`https://webdav.yandex.ru/Escale Repository` |enter|

Note that you will need to manually make this directory, for example from the web interface to your `Yandex.Disk space <https://disk.yandex.ru/client/disk>`_.

.. include:: wizard-part-2.txt

.. include:: wizard-part-3.txt

.. include:: wizard-part-4.txt

.. include:: wizard-part-5.txt

