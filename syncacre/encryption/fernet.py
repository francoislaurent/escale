# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from .encryption import Cipher

import cryptography.fernet


class Fernet(Cipher):
	"""
	See also `cryptography.io/en/latest/fernet <https://cryptography.io/en/latest/fernet/>`_.
	"""
	def __init__(self, passphrase):
		Cipher.__init__(self, passphrase)
		self.cipher = cryptography.fernet.Fernet(self.passphrase)

	def _encrypt(self, data):
		return self.cipher.encrypt(data)

	def _decrypt(self, data):
		return self.cipher.decrypt(data)

