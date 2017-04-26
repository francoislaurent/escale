# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

import tempfile
import os
from syncacre.base.essential import *


class Cipher(object):
	"""
	Partially abstract class that encrypts and decrypts file.

	A concrete `Cipher` class should implement :meth:`_encrypt` and :meth:`_decrypt`.

	Attributes:

		passphrase (str-like): arbitrarily long passphrase.

	"""
	def __init__(self, passphrase):
		if (PYTHON_VERSION == 3 and isinstance(passphrase, str)) or \
			(PYTHON_VERSION == 2 and isinstance(passphrase, unicode)):
			passphrase = passphrase.encode('utf-8')
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
		except Exception as e:
			fo.close()
			if auto:
				os.unlink(cipher)
			cipher = None
			print(e)
		return cipher

	def decrypt(self, cipher, plain=None, consume=True, makedirs=True):
		auto = not plain
		if auto:
			plain = tempfile.mkstemp()[1]
		elif makedirs:
			dirname = os.path.dirname(plain)
			if not os.path.isdir(dirname):
				os.makedirs(dirname)
		fo = open(plain, 'wb')
		try:
			with open(cipher, 'rb') as fi:
				fo.write(self._decrypt(fi.read()))
			fo.close()
			if consume:
				os.unlink(cipher)
		except:
			fo.close()
			if auto:
				os.unlink(plain)
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
		os.unlink(cipher)



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

