
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
::

        $ mkdir ~/Dropbox/Escale\ Repository

If not already done, install |escale| as detailled `elsewhere <http://escale.readthedocs.io/en/latest/install.html>`_:
::

        $ pip install --user escale

Run the |escale| configuration wizard in a terminal:
::

        $ escale -i

You may run into a license acceptance step that requires to answer two yes-no questions. 
You must accept the terms of the license if you want to use |escale|.
::

        Do you have knowledge of the CeCILL-C license and accept its terms? [NO/yes] yes
        Acceptance stored in file: '$HOME/.config/escale/acceptance'

If you set-up |escale| for the first time, you will 


.. |escale| replace:: **Escale**
.. |dropbox| replace:: **Dropbox**
