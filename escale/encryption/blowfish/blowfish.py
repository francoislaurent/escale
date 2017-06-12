# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from ..encryption import Cipher
import os

import blowfish # Python 3 only!


_iv_len = 8

try:
	_mode = dict(
			OFB=blowfish.Cipher.encrypt_ofb,
			CFB=blowfish.Cipher.encrypt_cfb,
		)
except AttributeError: # Python 2
	raise ImportError('the `blowfish` library is available for Python 3 only')


class Blowfish(Cipher):
	'''
	Blowfish encryption based on the `blowfish <https://pypi.python.org/pypi/blowfish>`_ library.
	'''
	def __init__(self, passphrase, mode='OFB'):
		Cipher.__init__(self, passphrase)
		self.mode = mode.upper()
		self.cipher = blowfish.Cipher(self.passphrase)

	def _encrypt(self, data, iv=None):
		if iv is None:
			iv = os.urandom(_iv_len)
		return iv + b''.join(_mode[self.mode](self.cipher, data, iv))

	def _decrypt(self, data, iv=None):
		if iv is None:
			iv = data[:_iv_len]
			data = data[_iv_len:]
		return b''.join(_mode[self.mode](self.cipher, data, iv))

