
#from syncacre.base import *
from .relay import Relay


class SSH(Relay):
	"""
	NOT IMPLEMENTED YET
	"""

	__protocol__ = 'ssh'

	def __init__(self, address, logger=None, **ignored):
		Relay.__init__(self, address, logger=logger)
		raise NotImplementedError


