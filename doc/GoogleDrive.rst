
Google Drive
============

Three options are available to synchronize over a Google Drive storage space:

* you can either mount your |googledrive| storage space in your local file system with an external tool (see the `Mounting locally`_ section)
* or you can use the |googledrive| backend provided in |escale| (see the `Synchronizing with drive`_ section)
* or else you can use the |rclone| backend provided in |escale| (see the `Synchronizing with rclone`_ section)


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

.. include:: wizard-part-1.txt

Let's now assume that your Google Drive is mounted on ``$HOME/GoogleDrive``.

You need to create a folder in there so that |escale| can temporary stored files and meta-information.
Let's call this folder ``Escale Repository``.

Respectivelly answer ``y`` and ``~/GoogleDrive/Escale Repository`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`~/GoogleDrive/Escale Repository` |enter|

.. include:: wizard-part-2.txt

.. include:: wizard-part-4.txt

.. include:: wizard-part-5.txt


Synchronizing with drive
------------------------

This section details how to use the partly-native client for Google Drive. 
This approach has the inconvenient of requiring the `drive <https://github.com/odeke-em/drive>`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 
If you already have it installed, then the approach described below is advised.

.. note:: you will need Go>=1.7. On Ubuntu 16, the officially supported Go version is too old.

You can alternatively install a compiled drive package.
This procedure is described in `this link <https://github.com/odeke-em/drive/blob/master/platform_packages.md>`_.

The backend in |escale| that makes use of the drive utility is referred to as a native backend because data are not buffered and all file transfers and accesses to your remote data are performed at call time.

Note that |escale| will assist you in installing drive but not the Go toolchain.

Please first install Go.
On Ubuntu 17 or later, this is as simple as:

.. parsed-literal::

	$ sudo apt install golang


.. include:: wizard-part-1.txt


Respectivelly answer ``y`` and ``googledrive://Escale Repository`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`googledrive://Escale Repository` |enter|


.. include:: wizard-part-2.txt

.. include:: wizard-part-4.txt


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


.. include:: wizard-part-5.txt

When you will run the *escale* command for the first time without the *-i* option, 
you will be instructed to copy and paste a link into a web browser, 
so that you can log in with |google| services.

Onced logged-in, the webpage will display a single line you can copy and paste back onto the 
command-line. 
This will permit |escale| to connect to your |googledrive| space.


Synchronizing with rclone
-------------------------

This section details how to use the partially-native client for Google Drive. 
This approach has the inconvenient of requiring the `rclone <https://rclone.org>`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 

The backend in |escale| that makes use of the rclone utility is referred to as a native backend because data are not buffered and all file transfers and accesses to your remote data are performed at call time.

Configuring RClone
^^^^^^^^^^^^^^^^^^

Install rclone and follow `this tutorial <https://rclone.org/drive/>`_ to set up rclone.

Note that instead of *remote* as a remote name, you can use any alternative name, e.g. *drive*.

Configuring Escale
^^^^^^^^^^^^^^^^^^

.. include:: wizard-part-1.txt


Respectivelly answer ``y`` and ``rclone://remote/Escale Repository`` to the next two questions, where ``remote`` is the remote name as defined for rclone:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`rclone://remote/Escale Repository` |enter|


.. include:: wizard-part-2.txt

.. include:: wizard-part-4.txt

.. include:: wizard-part-5.txt

