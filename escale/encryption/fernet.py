# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


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

