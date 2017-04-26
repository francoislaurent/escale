
#from syncacre.base.essential import *
from .relay import Relay


class FTP(Relay):
	"""
	NOT IMPLEMENTED YET
	"""

	__protocol__ = 'ftp'

	def __init__(self, address, logger=None, **ignored):
		Relay.__init__(self, address, logger=logger)
		raise NotImplementedError


