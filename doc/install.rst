
Installation
============

Check first the availability of |escale| in your favorite package manager.

From wheel
----------

|escale| is on `PyPI <https://pypi.python.org/pypi/escale/>`_::

        pip install --user escale

If you intend to use |escale| with a WebDAV service, request the *WebDAV* feature:
::

        pip install --user escale[WebDAV]

From source
-----------

You will need Python >= 2.7 or >= 3.5.
::

	git clone https://github.com/francoislaurent/escale.git
	cd escale
	pip install --user -e .

The ``-e`` option is necessary if you intend to update or modify the code and have the modifications reflected in your installed |escale|.

If you intend to use |escale| with a WebDAV service, request the *WebDAV* feature:
::

        pip install --user -e .[WebDAV]

Documentation
-------------

If you wish to compile the documentation and get a local copy of it, you will need Sphinx.
Once |escale| is installed, type:
::

	cd doc
	make html

The generated documentation will be available at ``_build/html/index.html`` from the ``doc`` repository.

.. note:: you may need to delete the ``_build`` directory before compiling the documentation again.

.. |escale| replace:: **Escale**
