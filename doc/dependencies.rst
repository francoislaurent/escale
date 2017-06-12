
Dependencies
============

python-daemon
-------------

As of version `0.5`, `python-daemon`_ is a non-optional dependency.

However |escale| can still run in non-daemon mode or emulate daemon mode with *nohup*. Especially |escalectl| automatically fall back on *nohup* if the *daemon* library is not available.

In addition, `python-daemon`_-2.1.2 has several dependencies such as the deprecated `lockfile`_ Python package.

To prevent |escale| from installing `python-daemon`_, get the source, edit the *setup.py* file in the root directory of the project, and remove the *python-daemon* mention in the *install_requires* list.

cryptography
------------

The `cryptography`_ library provides the default implemention for the encryption module in |escale|.

In Python3, the `blowfish`_ library offers an alternative. You will need to install the library and be careful to set ``encryption = blowfish.blowfish`` in the configuration file of all the clients.

Indeed the *cryptography* and *blowfish* backends for Blowfish encryption are not compatible and cannot interoperate.

.. |escale| replace:: **Escale**
.. |escalecmd| replace:: *escale*
.. |escalectl| replace:: *escalectl*
.. _python-daemon: https://pypi.python.org/pypi/python-daemon/
.. _lockfile: https://pypi.python.org/pypi/lockfile/
.. _cryptography: https://cryptography.io/en/latest/
.. _blowfish: https://pypi.python.org/pypi/blowfish/

