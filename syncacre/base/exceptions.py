# -*- coding: utf-8 -*-

# Copyright (c) 2017, Institut Pasteur
#   Contributor: François Laurent

# Copyright (c) 2017, François Laurent
#   contributions: MissingSetupFeature
from .essential import SYNCACRE_NAME

class UnrecoverableError(RuntimeError):
	pass

class MissingSetupFeature(ImportError):
	def __str__(self):
		return "install missing dependencies with 'pip install {}[{}]'".format(SYNCACRE_NAME, self.args[0])

