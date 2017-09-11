
Dropbox
=======

Two options are available to synchronize over a Dropbox storage space.

The recommended approach consists of using the `rclone`_-based backend provided in |escale|. See the `Synchronizing with rclone`_ section.

You can also use the |dropbox| proprietary client, mount your account space as a folder and run |escale| on a subdirectory in that folder. See the `Mounting locally`_ section.


Synchronizing with rclone
-------------------------

This section details how to use the partially-native client for |dropbox|. 
This approach has the disadvantage of requiring the `rclone`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 

The backend in |escale| that makes use of the rclone utility is referred to as a native backend because data are not buffered and all file transfers and accesses to your remote data are performed at call time.


Requirements
^^^^^^^^^^^^

You can either install and set up rclone following `this tutorial <https://rclone.org/dropbox/>`_ or let escale's configuration wizard do it for you. 

Note however that escale will not install the Go toolchain for you. 
Ensure that the go command is available:

.. parsed-literal::

	$ :strong:`go version`

This should show the version number of your installed Go distribution.
Otherwise please `install Go <https://golang.org/doc/install>`_.


You will also need a dedicated folder in your |dropbox| storage space. 
It will temporarily accommodate the files to be transfered and will permanently accommodate some meta files.

In this tutorial we make an ``Escale Repository`` folder at the root of the storage space.


Configuring Escale
^^^^^^^^^^^^^^^^^^

.. include:: wizard-part-1.txt


Answer ``dropbox://remote/Escale Repository`` to the second question, 
where ``remote`` is the remote name as defined for rclone 
and ``Escale Repository`` is the name of the folder that will accommodate the relay repository in your |dropbox| space:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`dropbox://remote/Escale Repository` |enter|


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
	See also: https://rclone.org/dropbox/
	...

From the last ellipsis begins the output of the ``rclone config`` command.
As instructed, please follow the steps described in the `tutorial for Dropbox <https://rclone.org/dropbox/>`_.


.. include:: wizard-part-5.txt



Mounting locally
----------------

Installing the proprietary Dropbox client
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You will find instructions on the `dropbox.com website <https://www.dropbox.com/install>`_.

Under Linux you may find the *nautilus-dropbox* package more convenient if you use Gnome.

Once the proprietary Dropbox client installed, you should find a *Dropbox* folder in your home directory.

Setting up a repository
^^^^^^^^^^^^^^^^^^^^^^^

First make a dedicated subdirectory inside your *Dropbox* folder to accommodate the said relay repository.
For example in a terminal you can type:

.. parsed-literal::

        $ :strong:`mkdir ~/Dropbox/Escale\\ Repository`

.. include:: wizard-part-1.txt

Respectivelly answer ``y`` and ``~/Dropbox/Escale Repository`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Request help with '?'
	Path of the locally accessible relay repository (required): :strong:`~/Dropbox/Escale Repository` |enter|


.. include:: wizard-part-2.txt

.. include:: wizard-part-4.txt

.. include:: wizard-part-5.txt
