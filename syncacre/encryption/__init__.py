# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from .encryption import Cipher, Plain
from syncacre.base.exceptions import MissingSetupFeature

__all__ = ['__ciphers__', '__extra_ciphers__', 'by_cipher', 'Cipher', 'Plain']


__ciphers__ = dict(plain=Plain)

# `__extra_ciphers__` is a ``dict`` that combines cipher identifiers
# with corresponding setup features or modules.
# modules are differentiated from features as they begin with a dot.
__extra_ciphers__ = {}


def _blowfish(backend=None):
	cipher = 'blowfish'
	if backend:
		cipher = '.'.join((cipher, backend))
	return cipher
try:
	from .blowfish import Blowfish, backends, extra_backends
except ImportError:
	__extra_ciphers__[_blowfish()] = 'Blowfish' # setup feature
	# TODO: automate backend extraction
	extra_backends = ['blowfish', 'cryptography']
	for backend in extra_backends:
		__extra_ciphers__[_blowfish(backend)] = 'Blowfish' # setup feature
else:
	__all__.append('Blowfish')
	__ciphers__[_blowfish()] = Blowfish
	for backend, implementation in backends.items():
		__ciphers__[_blowfish(backend)] = implementation
	for backend in extra_backends:
		__extra_ciphers__[_blowfish(backend)] = '.blowfish.'+backend # module

try:
	from .fernet import Fernet
except ImportError:
	__extra_ciphers__['fernet'] = 'Fernet' # setup feature
else:
	__all__.append('Fernet')
	__ciphers__['fernet'] = Fernet


def by_cipher(cipher):
	cipher = cipher.lower() # should we?
	try:
		return __ciphers__[cipher]
	except KeyError as e:
		try:
			feature_or_module = __extra_ciphers__[cipher]
		except:
			raise e
		else:
			if feature_or_module[0] == '.': # module
				import importlib
				# import module and raise an ImportError to give
				# directions to the user (or developper)
				importlib.import_module(feature_or_module,
						package='syncacre.encryption')
			else: # setup feature
				raise MissingSetupFeature(feature_or_module)

