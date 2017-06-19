
Google Drive
============

To synchronize your data using |googledrive| as a relay storage, you should first make a new directory to accommodate the relay repository.

To synchronize using this remote directory, you have two options:

* you can either mount your |googledrive| storage space in your local file system with an external tool (see the `Mounting locally`_ section)
* or you can use the |googledrive| backend provided in |escale| (see the `Synchronizing with drive`_)


Mounting locally
----------------

The approach described in this section consists of mounting your Google Drive storage space as a folder accessible in your local file system.

|google| offers for download its `Drive app <https://www.google.com/drive/download/>`_ for |macos|. 
|macos| can therefore go for this solution.

However Linux users may fall back on the following open-source solutions:

* `google-drive-ocamlfuse <https://github.com/astrada/google-drive-ocamlfuse>`_
* `rclone <https://rclone.org>`_ mount
* maybe gnome-control-center + gnome-online-accounts

You may find the following `guide <https://linuxnewbieguide.org/how-to-use-google-drive-in-linux/>`_ interesting.

Configuring Escale
^^^^^^^^^^^^^^^^^^

.. todo:: write this section

.. include:: wizard-first-steps.txt

Let's now assume that your Google Drive is mount on ``$HOME/GoogleDrive``.
You need to create a folder in there so that |escale| can temporary stored files and meta-information.
Let's call this folder ``Escale Repository``.

Respectivelly answer ``y`` and ``~/GoogleDrive/Escale Repository`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Enter the path of the locally accessible repository.
	If you intend to use Google Drive mounted with
	the drive utility, you can alternatively specify:
	  googledrive:///mountpoint[//path]
	where '/mountpoint' is the absolute path to a local
	mount and 'path' is the path of the relay directory
	relative to the mount point.
	Path of the locally accessible relay repository (required): :strong:`~/GoogleDrive/Escale Repository` |enter|

.. include:: wizard-last-steps.txt

Your client is ready and can be launched with:

.. parsed-literal::

	$ :strong:`escale`

or as a daemon:

.. parsed-literal::

	$ :strong:`escale -d`

You can make your terminal continuously flush the logs with:

.. parsed-literal::

	$ :strong:`tail -f ~/.config/escale/escale.log`



Synchronizing with drive
------------------------

This section details how to use the native client for Google Drive. 
This approach has the inconvenient of requiring the `drive <https://github.com/odeke-em/drive>`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 
If you already have it installed, then the approach described below is advised.

.. note:: you will need Go>=1.7. On Ubuntu 16, the officially supported Go version is too old.

You can alternatively install a compiled drive package.
This procedure is described in `this link <https://github.com/odeke-em/drive/blob/master/platform_packages.md>`_.

The backend in |escale| that makes use of the drive utility is referred to as a native backend because data are not buffer and every file transfers and accesses to your remote data are performed at call time.

Note that |escale| will assist you in installing drive but not the Go toolchain.
Please first install Go.
On Ubuntu, this is as simple as::

	sudo apt install golang


.. include:: wizard-first-steps.txt


Respectivelly answer ``y`` and ``googledrive://Escale Repository`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Enter the path of the locally accessible repository.
	If you intend to use Google Drive mounted with
	the drive utility, you can alternatively specify:
	  googledrive:///mountpoint[//path]
	where '/mountpoint' is the absolute path to a local
	mount and 'path' is the path of the relay directory
	relative to the mount point.
	Path of the locally accessible relay repository (required): :strong:`googledrive://Escale Repository` |enter|


.. include:: wizard-last-steps.txt


The wizard will now assist you in installing the drive utility, if necessary.

.. parsed-literal::

        If you don't have 'drive' installed, leave it empty:
        Drive binary: |enter|
        The 'drive' Go package is going to be installed.
        Do you want to continue? [Y/n] |enter|
        Cannot find the 'GOPATH' environment variable.
        Where do you want Go packages to be installed? [~/golang] |enter|
        go get -u github.com/odeke-em/drive/drive-google
        ...
        'drive' installed.
	Do you want to add/edit another section? [N/y] |enter|


Your client is ready and can be launched with:

.. parsed-literal::

	$ :strong:`escale`

or as a daemon:

.. parsed-literal::

	$ :strong:`escale -d`

You can make your terminal continuously flush the logs with:

.. parsed-literal::

	$ :strong:`tail -f ~/.config/escale/escale.log`


