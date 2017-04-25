# -*- coding: utf-8 -*-

backends = {}

try:
	from .blowfish import Blowfish
except ImportError:
	pass
else:
	backends['blowfish'] = Blowfish

try:
	from .cryptography import Blowfish # last is default
except ImportError:
	pass
else:
	backends['cryptography'] = Blowfish

__all__ = ['Blowfish', 'backends']

