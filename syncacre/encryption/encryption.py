
import tempfile
import os


class Cipher(object):

	def __init__(self, passphrase):
		self.passphrase = passphrase

	def _encrypt(self, data):
		raise NotImplementedError('abstract method')

	def _decrypt(self, data):
		raise NotImplementedError('abstract method')

	def encrypt(self, plain, cipher=None):
		auto = not cipher
		if auto:
			cipher = tempfile.mkstemp()
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
			plain = tempfile.mkstemp()
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

	def prepare(self, cipher):
		return tempfile.mkstemp()

	def finalize(self, cipher):
		os.delete(cipher)



class Plain(Cipher):

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

