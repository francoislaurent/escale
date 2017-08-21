
Dropbox
=======

Two options are available to synchronize over a Dropbox storage space:

* you can either use the |dropbox| proprietary client, mount your account space as a folder and run |escale| on a subdirectory in that folder (see the `Mounting locally`_ section)
* or you can use the |rclone| backend provided in |escale| (see the `Synchronizing with rclone`_ section)

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


Synchronizing with rclone
-------------------------

This section details how to use the partially-native client for Dropbox. 
This approach has the inconvenient of requiring the `rclone <https://rclone.org>`_ utility that in turn depends on the `Go toolchain <https://golang.org/doc/install>`_.

Installing the Go toolchain may add a significant amount of used space (like 160MB on Linux for example). 

The backend in |escale| that makes use of the rclone utility is referred to as a native backend because data are not buffered and all file transfers and accesses to your remote data are performed at call time.

Configuring RClone
^^^^^^^^^^^^^^^^^^

Install rclone and follow `this tutorial <https://rclone.org/drive/>`_ to set up rclone.

Note that instead of *remote* as a remote name, you can use any alternative name, e.g. *dropbox*.

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

