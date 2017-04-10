
from .encryption import Cipher

try:
	import cryptography.hazmat.primitives.ciphers.algorithms as cryptography


	class Blowfish(Cipher):
		def __init__(self, passphrase):
			if isinstance(passphrase, str):
				passphrase = passphrase.encode('utf-8')
			self.cipher = cryptography.Blowfish(passphrase)

		def _encrypt(self, data):
			return self.cipher.encryptor().update(data)

		def _decrypt(self, data):
			return self.cipher.decryptor().update(data)



except ImportError as e:
	try:
		import blowfish # Python 3 only!
	except ImportError:
		raise e


	class Blowfish(Cipher):
		def __init__(self, passphrase):
			if isinstance(passphrase, str):
				passphrase = passphrase.encode('utf-8')
			self.cipher = blowfish.Cipher(passphrase)

		def _encrypt(self, data):
			return b"".join(self.cipher.encrypt_ecb(data)) # ecb chosen arbitrarily

		def _decrypt(self, data):
			return b"".join(self.cipher.decrypt_ecb(data))

