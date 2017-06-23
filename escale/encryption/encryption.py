# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import tempfile
import os
from escale.base.essential import *
from escale.base.exceptions import ExpressInterrupt


class Cipher(object):
	"""
	Partially abstract class that encrypts and decrypts file.

	A concrete `Cipher` class should implement :meth:`_encrypt` and :meth:`_decrypt`.

	Attributes:

		passphrase (str-like): arbitrarily long passphrase.

		_temporary_files (list): list of paths to existing temporary files.

	"""
	def __init__(self, passphrase):
		if (PYTHON_VERSION == 3 and isinstance(passphrase, str)) or \
			(PYTHON_VERSION == 2 and isinstance(passphrase, unicode)):
			passphrase = passphrase.encode('utf-8')
		self.passphrase = passphrase
		self._temporary_files = []

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
		__open__ = open
		auto = not cipher
		if auto:
			fo, cipher = tempfile.mkstemp()
			# `fo` has to be converted into a file object with `open` (Py3)
			# or `os.fdopen` (Py2, Py3)
			__open__ = os.fdopen
			self._temporary_files.append(cipher)
		else:
			fo = cipher # to be opened with `open`
		try:
			with __open__(fo, 'wb') as fo:
				with open(plain, 'rb') as fi:
					_c = self._encrypt(fi.read())
					#print(_c)
					fo.write(_c)
		except ExpressInterrupt:
			raise
		except Exception as e:
			if auto:
				os.unlink(cipher)
				self._temporary_files.remove(cipher)
			cipher = None
			print(e)
		return cipher

	def decrypt(self, cipher, plain=None, consume=True, makedirs=True):
		__open__ = open
		auto = not plain
		if auto:
			fo, plain = tempfile.mkstemp()
			# `fo` has to be converted into a file object with `open` (Py3)
			# or `os.fdopen` (Py2, Py3)
			__open__ = os.fdopen
			self._temporary_files.append(plain)
		else:
			if makedirs:
				dirname = os.path.dirname(plain)
				if not os.path.isdir(dirname):
					os.makedirs(dirname)
			fo = plain
		try:
			with __open__(fo, 'wb') as fo:
				with open(cipher, 'rb') as fi:
					fo.write(self._decrypt(fi.read()))
		except ExpressInterrupt:
			raise
		except Exception as e:
			if auto:
				os.unlink(plain)
				self._temporary_files.remove(plain)
			plain = None
			print(e)
		else:
			if consume:
				os.unlink(cipher)
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
		fd, f = tempfile.mkstemp()
		os.close(fd)
		self._temporary_files.append(f)
		return f

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
		try:
			self._temporary_files.remove(cipher)
		except ValueError:
			pass

	def __del__(self):
		for f in self._temporary_files:
			try:
				os.unlink(f)
			except OSError:
				pass



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

	def __del__(self):
		pass

