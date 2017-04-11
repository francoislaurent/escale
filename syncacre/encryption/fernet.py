
from syncacre.base import *
from .encryption import Cipher

import cryptography.fernet
import base64



class Fernet(Cipher):
	"""
	See also `cryptography.io/en/latest/fernet <https://cryptography.io/en/latest/fernet/>`_.
	"""
	def __init__(self, passphrase):
		# encode
		if PYTHON_VERSION == 3:
			if isinstance(passphrase, str):
				passphrase = passphrase.encode('utf-8')
		#passphrase = base64.urlsafe_b64encode(passphrase)
		# pad
		#_len, _LEN = len(passphrase), 32*8
		#if _len < _LEN:
		#	pad = b'00000000000000000000000000000000000000000000000000000'
		#	passphrase += pad[_len:_LEN]
		#elif _LEN < _len:
		#	passphrase = passphrase[:_LEN]
		self.cipher = cryptography.fernet.Fernet(passphrase)

	def _encrypt(self, data):
		return self.cipher.encrypt(data)

	def _decrypt(self, data):
		return self.cipher.decrypt(data)

