
from .encryption import Cipher, Plain

__all__ = ['__ciphers__', 'by_cipher', 'Cipher', 'Plain']

__ciphers__ = dict(plain=Plain)

import six

if six.PY3:
	from .blowfish import Blowfish
	__all__.append('Blowfish')
	__ciphers__['blowfish'] = Blowfish

def by_cipher(cipher):
	return __ciphers__[cipher]

