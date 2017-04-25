
from .encryption import Cipher, Plain

__all__ = ['__ciphers__', 'by_cipher', 'Cipher', 'Plain']

__ciphers__ = dict(plain=Plain)

import sys

if sys.version_info[0] == 3:
	pass
	# Blowfish is temporarily removed. See issue https://github.com/francoislaurent/syncacre/issues/15
	from .blowfish import Blowfish
	__all__.append('Blowfish')
	__ciphers__['blowfish'] = Blowfish

try:
	from .fernet import Fernet
	__all__.append('Fernet')
	__ciphers__['fernet'] = Fernet
except ImportError:
	pass


def by_cipher(cipher):
	return __ciphers__[cipher]

