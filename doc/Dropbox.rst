
Dropbox
-------

|escale| does not feature any native client for |dropbox|. You can still use the |dropbox| proprietary client, mount your account space as a folder and run |escale| on a subdirectory in that folder.

Installing the proprietary Dropbox client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You will find instructions on the `dropbox.com website <https://www.dropbox.com/install>`_.

Under Linux you may find the *nautilus-dropbox* package more convenient if you use Gnome.

Once the proprietary Dropbox client installed, you should find a *Dropbox* folder in your home directory.

Setting up a repository
~~~~~~~~~~~~~~~~~~~~~~~

First make a dedicated subdirectory inside your *Dropbox* folder to accommodate the said relay repository.
For example in a terminal you can type:

.. parsed-literal::

        $ :strong:`mkdir ~/Dropbox/Escale\\ Repository`

If not already done, install |escale| as detailled `elsewhere <install.html>`_:

.. parsed-literal::

        $ :strong:`pip install --user escale`

Run the |escale| configuration wizard in a terminal:

.. parsed-literal::

        $ :strong:`escale -i`

You may run into a license acceptance step that requires to answer two yes-no questions. 
You must accept the terms of the license if you want to use |escale|.

.. parsed-literal::

        Do you have knowledge of the CeCILL-C license and accept its terms? [NO/yes] :strong:`yes`
        Acceptance stored in file: '$HOME/.config/escale/acceptance'

.. note:: User-supplied text is shown in bold characters.

	Carriage returns are indicated by |enter|.

If you set-up |escale| for the first time, you will be requested the path of the folder you want to synchronize:

.. parsed-literal::

	Editing configuration file '$HOME/.config/escale/escale.conf'
	Path of your local repository (required): :strong:`test/dropbox` |enter|
	Making directory '$HOME/github/escale/test/dropbox'

Respectivelly answer ``y`` and ``~/Dropbox`` to the next two questions:

.. parsed-literal::

	Is the relay repository locally mounted in the file system? [N/y] :strong:`y` |enter|
	Enter the path of the locally accessible repository.
	If you intend to use Google Drive mounted with
	the drive utility, you can alternatively specify:
	  googledrive:///mountpoint[//path]
	where '/mountpoint' is the absolute path to a local
	mount and 'path' is the path of the relay directory
	relative to the mount point.
	Path of the locally accessible relay repository (required): :strong:`~/Dropbox` |enter|

.. include:: wizard-common.rst


.. |dropbox| replace:: **Dropbox**
