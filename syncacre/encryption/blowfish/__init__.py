# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

backends = {}
extra_backends = {}

try:
	from .blowfish import Blowfish
except ImportError:
	extra_backends['blowfish'] = 'blowfish'
else:
	backends['blowfish'] = Blowfish

try:
	from .cryptography import Blowfish # last is default
except ImportError:
	extra_backends['cryptography'] = 'cryptography'
else:
	backends['cryptography'] = Blowfish

__all__ = ['Blowfish', 'backends', 'extra_backends']

