# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

#from syncacre.base.essential import *
from .relay import Relay


class SSH(Relay):
	"""
	NOT IMPLEMENTED YET

	SSH support is suspended as commented in `issue #3 <https://github.com/francoislaurent/syncacre/issues/3>`_.
	"""

	__protocol__ = 'ssh'

	def __init__(self, address, logger=None, **ignored):
		Relay.__init__(self, address, logger=logger)
		raise NotImplementedError


