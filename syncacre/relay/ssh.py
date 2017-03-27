
from .relay import Relay


class SSH(Relay):
	"""
	NOT IMPLEMENTED YET
	"""

	__protocol__ = 'ssh'

	def __init__(self, address, **ignored):
		Relay.__init__(self, address)
		raise NotImplementedError


