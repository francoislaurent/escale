
Dropbox
=======

|escale| does not feature any native client for |dropbox|. 
You can still use the |dropbox| proprietary client, mount your account space as a folder and run |escale| on a subdirectory in that folder.

Installing the proprietary Dropbox client
-----------------------------------------

You will find instructions on the `dropbox.com website <https://www.dropbox.com/install>`_.

Under Linux you may find the *nautilus-dropbox* package more convenient if you use Gnome.

Once the proprietary Dropbox client installed, you should find a *Dropbox* folder in your home directory.

Setting up a repository
-----------------------

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

