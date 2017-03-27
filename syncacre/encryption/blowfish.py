
from .encryption import Cipher
import blowfish # Python 3 only!


class Blowfish(Cipher):
	def __init__(self, passphrase):
		if isinstance(passphrase, str):
			passphrase = passphrase.encode('utf-8')
		self.cipher = blowfish.Cipher(passphrase)

	def _encrypt(self, data):
		return b"".join(self.cipher.encrypt_ecb(data)) # ecb chosen arbitrarily

	def _decrypt(self, data):
		return b"".join(self.cipher.decrypt_ecb(data))

