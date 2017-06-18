
Yandex.Disk
===========

|escale| can operate with the Yandex.Disk WebDAV server at webdav.yandex.ru.

.. include:: wizard-first-steps

You have to choose a name for the directory that will accommodate the relay repository. Here we choose ``Escale Repository`` as a name:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] |enter|
	A host address should be in the form:
	  protocol:///servername[:port][/path]
	if 'protocol' is any of:
          'ftp', 'ftps', 'http', 'https' or 'webdav'
        Some protocols do not even need a server name, e.g.: 
          googledrive[://path]
        Address of the relay repository (required): :strong:`https://webdav.yandex.ru/Escale Repository` |enter|


.. exclude:: wizard-last-steps


Your client is ready and can be launched with:

.. parsed-literal::

	$ :strong:`escale`

or as a daemon:

.. parsed-literal::

	$ :strong:`escale -d`

You can make your terminal continuously flush the logs with:

.. parsed-literal::

	$ :strong:`tail -f ~/.config/escale/escale.log`

