
Yandex.Disk
===========

Two options are available to synchronize over a Yandex.Disk storage space.

The recommended approach consists of using the `rclone`_-based backend provided in |escale|. See the `Synchronizing with rclone`_ section.


Synchronizing with rclone
-------------------------

This section details how to use the partially-native client for |yandex|. 
This approach has the disadvantage of requiring the `rclone`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 

The backend in |escale| that makes use of the rclone utility is referred to as a native backend because data are not buffered and all file transfers and accesses to your remote data are performed at call time.


Requirements
^^^^^^^^^^^^

You can either install and set up rclone following `this tutorial <https://rclone.org/yandex/>`_ or let escale's configuration wizard do it for you. 

Note however that escale will not install the Go toolchain for you. 
Ensure that the go command is available:

.. parsed-literal::

	$ :strong:`go version`

This should show the version number of your installed Go distribution.
Otherwise please `install Go <https://golang.org/doc/install>`_.


You will also need a dedicated folder in your |yandex| storage space. 
It will temporarily accommodate the files to be transfered and will permanently accommodate some meta files.

In this tutorial we make an ``Escale Repository`` folder at the root of the storage space.


Configuring Escale
^^^^^^^^^^^^^^^^^^

.. include:: wizard-part-1.txt


Answer ``yandex://remote/Escale Repository`` to the second question, 
where ``remote`` is the remote name as defined for rclone 
and ``Escale Repository`` is the name of the folder that will accommodate the relay repository in your |yandex| space:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`yandex://remote/Escale Repository` |enter|


.. include:: wizard-part-2.txt

.. include:: wizard-part-4.txt


The wizard will now assist you in installing the rclone utility, if missing.

.. parsed-literal::

        If you don't have 'rclone' installed, leave it empty:
        RClone binary: |enter|
        The 'rclone' Go package is going to be installed.
        Do you want to continue? [Y/n] |enter|
        Cannot find the 'GOPATH' environment variable.
        Where do you want Go packages to be installed? [~/golang] |enter|
        go get -u github.com/ncw/rclone
        ...
        'rclone' installed.
	Running 'rclone config'
	See also: https://rclone.org/yandex/
	...

From the last ellipsis begins the output of the ``rclone config`` command.
As instructed, please follow the steps described in the `tutorial for Yandex Disk <https://rclone.org/yandex/>`_.


.. include:: wizard-part-5.txt

.. attention:: You may have to empty the trash from time to time for escale to work smoothly.


Synchronizing with the native WebDAV backend
--------------------------------------------

.. attention:: The native WebDAV client no longer works properly with Yandex.Disk.
   Please favor the rclone backend.

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

