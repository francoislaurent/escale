
escale.encryption package
=========================

.. automodule:: escale.encryption
    :members:
    :show-inheritance:


escale.encryption.encryption module
-----------------------------------

.. automodule:: escale.encryption.encryption
    :members:
    :undoc-members:
    :show-inheritance:


escale.encryption.fernet module
-------------------------------

The :mod:`~escale.encryption.fernet` module provides the recommended implementation for the :class:`Cipher` class. 
It is based on the `cryptography library <https://cryptography.io/en/latest/fernet/>`_.

.. automodule:: escale.encryption.fernet
    :members:
    :undoc-members:
    :show-inheritance:


escale.encryption.blowfish module
---------------------------------

The :mod:`~escale.encryption.blowfish` module is actually a package that accomodates several implementations refered to as backends.

The :mod:`~escale.encryption.blowfish.cryptography` backend prevails if the cryptography library is available (see `here <https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/?highlight=blowfish#weak-ciphers>`_). 
Otherwise, :class:`~escale.encryption.blowfish.Blowfish` is implemented with :mod:`~escale.encryption.blowfish.blowfish` as a backend (`blowfish`_ library).

.. automodule:: escale.encryption.blowfish
    :members:
    :undoc-members:
    :show-inheritance:


escale.encryption.blowfish.blowfish module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: escale.encryption.blowfish.blowfish
    :members:
    :undoc-members:
    :show-inheritance:


escale.encryption.blowfish.cryptography module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: escale.encryption.blowfish.cryptography
    :members:
    :undoc-members:
    :show-inheritance:

