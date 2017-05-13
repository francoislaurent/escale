# -*- coding: utf-8 -*-

# Copyright (c) 2017, Institut Pasteur
#   Contributor: François Laurent

# Copyright (c) 2017, François Laurent
#   contributions: MissingSetupFeature
from .essential import PROGRAM_NAME


class UnrecoverableError(RuntimeError):
	"""
	This exception signals that the Python environment should be reset.
	"""
	pass

class MissingSetupFeature(ImportError):
	"""
	This exception helps document missing dependencies at runtime.

	It is designed for setup features that select optional relay and encryption backends.
	"""
	def __str__(self):
		return "install missing dependencies with 'pip install {}[{}]'".format(PROGRAM_NAME, self.args[0])

