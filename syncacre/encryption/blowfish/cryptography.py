# -*- coding: utf-8 -*-

from ..encryption import Cipher
import os

import cryptography.hazmat.primitives.ciphers.algorithms as algorithms
import cryptography.hazmat.primitives.ciphers.modes as modes
import cryptography.hazmat.primitives.ciphers as cryptography
import cryptography.hazmat.backends as backend


_iv_len = 8

_mode = dict(
		OFB=modes.OFB,
		CFB=modes.CFB,
	)

class Blowfish(Cipher):
	'''
	Blowfish encryption based on the `cryptography <https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/?highlight=blowfish#weak-ciphers>`_ library.
	'''
	def __init__(self, passphrase, mode='OFB'):
		Cipher.__init__(self, passphrase)
		self.mode = mode.upper()
		self.cipher = algorithms.Blowfish(self.passphrase)
		self.backend = backend.default_backend()

	def _encrypt(self, data, iv=None):
		if iv is None:
			iv = os.urandom(_iv_len)
		cipher = cryptography.Cipher(self.cipher, mode=_mode[self.mode](iv),
				backend=self.backend).encryptor()
		return b''.join([iv, cipher.update(data)])

	def _decrypt(self, data, iv=None):
		if iv is None:
			iv = data[:_iv_len]
			data = data[_iv_len:]
		cipher = cryptography.Cipher(self.cipher, mode=_mode[self.mode](iv),
				backend=self.backend).decryptor()
		return cipher.update(data)

