.. SynCÀCRe documentation master file, adapted from a file created by
   sphinx-quickstart on Tue Jan 24 11:46:04 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SynCÀCRe documentation
======================

|syncacre| is a client-to-client synchronization program based on external relay storage (French: SYNchronisation Client-À-Client par RElai)

Files can be transfered between nodes with no administration privileges. All nodes are clients. Consequently they can operate from behind restrictive firewalls.

All what |syncacre| needs is an external storage space such as an SSH or WebDAV account on a server. The nodes running |syncacre| can upload their respective files and download from the remote account the files they don't have locally.

The external passive storage can have limited storage space and files are deleted from the server one every client got a copy.

The server itself may not be trusted and files can be encrypted before they are uploaded.


Installation
------------

You will need Python >= 2.7 or >= 3.5.
::

	git clone https://github.com/francoislaurent/syncacre.git
	cd syncacre
	pip install --user -e .

The ``-e`` option is necessary if you intend to update or modify the code and have the modifications reflected in your installed |syncacre|.

To compile the documentation and get a local copy, after installing |syncacre| do:
::

	cd doc
	make html

The generated documentation will be available at ``_build/html/index.html`` from the ``doc`` repository.


Commandline
-----------
::

	> python -m syncacre -c <path-to-conf-file>


Configuration file
------------------

.. todo:: This section is empty. Alternatively you can look at examples in the ``conf`` directory.


API
---

.. toctree::
   :maxdepth: 1

   relay
   manager
   encryption

.. Indices and tables
.. ------------------

.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

.. |syncacre| replace:: **Syncacre**

