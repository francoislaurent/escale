
import tempfile
import os


class Cipher(object):
	"""
	Partially abstract class that encrypts and decrypts file.

	A concrete `Cipher` class should implement :meth:`_encrypt` and :meth:`_decrypt`.

	Attributes:

		passphrase (str): arbitrarily long passphrase.

	"""
	def __init__(self, passphrase):
		self.passphrase = passphrase

	def _encrypt(self, data):
		"""
		Encrypts binary data.

		Arguments:

			data (bytes): plain data.

		Returns:

			bytes: encrypted data.
		"""
		raise NotImplementedError('abstract method')

	def _decrypt(self, data):
		"""
		Decrypts binary data.

		Arguments:

			data (bytes): encrypted data.

		Returns:

			bytes: plain data.
		"""
		raise NotImplementedError('abstract method')

	def encrypt(self, plain, cipher=None):
		auto = not cipher
		if auto:
			cipher = tempfile.mkstemp()[1]
		fo = open(cipher, 'wb')
		try:
			with open(plain, 'rb') as fi:
				fo.write(self._encrypt(fi.read()))
			fo.close()
		except:
			fo.close()
			if auto:
				os.delete(cipher)
			cipher = None
		return cipher

	def decrypt(self, cipher, plain=None, consume=True):
		auto = not plain
		if auto:
			plain = tempfile.mkstemp()[1]
		fo = open(plain, 'wb')
		try:
			with open(cipher, 'rb') as fi:
				fo.write(self._decrypt(fi.read()))
			fo.close()
			if consume:
				os.delete(cipher)
		except:
			fo.close()
			if auto:
				os.delete(plain)
			plain = None
		return plain

	def prepare(self, plain):
		"""
		Example:
		::

			# plain_file may refer to a non-existing file
			temp_file = cipher.prepare(plain_file)
			# get encrypted file as `temp_file`,
			# and then decrypt it into `target_file`:
			cipher.decrypt(temp_file, plain_file)
			# `temp_file` is no longer available
		"""
		return tempfile.mkstemp()[1]

	def finalize(self, cipher):
		"""
		Example:
		::

			temp_file = cipher.encrypt(plain_file)
			# manipulate encrypted file `temp_file`
			cipher.finalize(temp_file)
			# `temp_file` is no longer available
		"""
		os.delete(cipher)



class Plain(Cipher):
	"""
	Concrete implementation of `Cipher` that actually does not cipher.
	"""
	def __init__(self, *ignored):
		pass

	def _encrypt(self, data):
		return data

	def _decrypt(self, data):
		return data

	def encrypt(self, plain, cipher=None):
		if cipher and plain != cipher:
			Cipher.encrypt(self, plain, cipher)
		else:
			return plain

	def decrypt(self, cipher, plain=None, consume=False):
		if plain and plain != cipher:
			Cipher.decrypt(self, cipher, plain, consume)
		else:
			return cipher

	def prepare(self, plain):
		return plain

	def finalize(self, cipher):
		pass

