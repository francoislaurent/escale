
from .encryption import Cipher

import cryptography.fernet


class Fernet(Cipher):
	"""
	See also `cryptography.io/en/latest/fernet <https://cryptography.io/en/latest/fernet/>`_.
	"""
	def __init__(self, passphrase):
		if isinstance(passphrase, str):
			passphrase = passphrase.encode('utf-8')
		self.cipher = cryptography.fernet.Fernet(passphrase)

	def _encrypt(self, data):
		return self.cipher.encrypt(data)

	def _decrypt(self, data):
		return self.cipher.decrypt(data)

