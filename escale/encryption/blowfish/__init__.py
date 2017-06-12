# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


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

