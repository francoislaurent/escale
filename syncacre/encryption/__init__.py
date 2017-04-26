# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from .encryption import Cipher, Plain

__all__ = ['__ciphers__', 'by_cipher', 'Cipher', 'Plain']

__ciphers__ = dict(plain=Plain)

import sys

try:
	from .blowfish import Blowfish, backends
except ImportError:
	pass
else:
	__all__.append('Blowfish')
	__ciphers__['blowfish'] = Blowfish
	for backend, implementation in backends.items():
		__ciphers__['blowfish.'+backend] = implementation

try:
	from .fernet import Fernet
except ImportError:
	pass
else:
	__all__.append('Fernet')
	__ciphers__['fernet'] = Fernet


def by_cipher(cipher):
	return __ciphers__[cipher.lower()]

