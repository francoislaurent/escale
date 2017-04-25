# -*- coding: utf-8 -*-

from ..encryption import Cipher
import os

import blowfish # Python 3 only!


_iv_len = 8

_mode = dict(
		OFB=blowfish.Cipher.encrypt_ofb,
		CFB=blowfish.Cipher.encrypt_cfb,
	)

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

