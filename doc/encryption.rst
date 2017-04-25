
syncacre.encryption package
===========================

.. automodule:: syncacre.encryption
    :members:
    :show-inheritance:


syncacre.encryption.encryption module
-------------------------------------

.. automodule:: syncacre.encryption.encryption
    :members:
    :undoc-members:
    :show-inheritance:


syncacre.encryption.blowfish module
-----------------------------------

The :mod:`~syncacre.encryption.blowfish` module is actually a package that accomodates several implementations refered to as backends.

The :mod:`~syncacre.encryption.blowfish.cryptography` backend prevails if the `cryptography <https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/?highlight=blowfish#weak-ciphers>`_ library is available. 
Otherwise, :class:`~syncacre.encryption.blowfish.Blowfish` is implemented with :mod:`~syncacre.encryption.blowfish.blowfish` as a backend (`blowfish <https://pypi.python.org/pypi/blowfish>`_ library).

.. automodule:: syncacre.encryption.blowfish
    :members:
    :undoc-members:
    :show-inheritance:


syncacre.encryption.blowfish.blowfish module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: syncacre.encryption.blowfish.blowfish
    :members:
    :undoc-members:
    :show-inheritance:


syncacre.encryption.blowfish.cryptography module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: syncacre.encryption.blowfish.cryptography
    :members:
    :undoc-members:
    :show-inheritance:

