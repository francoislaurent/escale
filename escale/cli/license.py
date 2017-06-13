# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import os
from escale import *
from escale.base.config import *
from escale.base.exceptions import LicenseError
from .format import *

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass


terms = """
Copyright © François Laurent (2017)
Copyright © Institut Pasteur (2017)

Escale is a computer program whose purpose is to synchronize files 
between clients that operate behind restrictive firewalls.

This software is governed by the CeCILL-C license under French law and
abiding by the rules of distribution of free software.  You can  use, 
modify and/ or redistribute the software under the terms of the CeCILL-C
license as circulated by CEA, CNRS and INRIA at the following URL
"http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html". 

As a counterpart to the access to the source code and  rights to copy,
modify and redistribute granted by the license, users are provided only
with a limited warranty  and the software's author,  the holder of the
economic rights,  and the successive licensors  have only  limited
liability. 

In this respect, the user's attention is drawn to the risks associated
with loading,  using,  modifying and/or developing or reproducing the
software by the user in light of its specific status of free software,
that may mean  that it is complicated to manipulate,  and  that  also
therefore means  that it is reserved for developers  and  experienced
professionals having in-depth computer knowledge. Users are therefore
encouraged to load and test the software's suitability as regards their
requirements in conditions enabling the security of their systems and/or 
data to be ensured and,  more generally, to use and operate it in the 
same conditions as regards security. 

"""

acceptance_mention = """
The fact that the present acceptance file exists on this machine means 
that you had knowledge of the CeCILL-C license and that you accepted 
its terms.
"""


acceptance_files = [
		os.path.expanduser('~/.config/escale/acceptance'),
		os.path.expanduser('~/.escale/acceptance'),
		]


def check_license_acceptance(accept=False):
	acceptance_text = terms + acceptance_mention
	for file in acceptance_files:
		if os.path.isfile(file):
			with open(file, 'r') as f:
				content = f.read()
			if content == acceptance_text:
				return
			else:
				os.unlink(file)
	if not accept:
		print(terms)
		license = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'LICENSE')
		if os.path.isfile(license):
			answer = input(decorate_line('do you want to read the license full text now? [YES/no] '))
			if not answer or answer[0] in 'yY':
				with open(license, 'r') as f:
					content = f.read()
				print(content)
		answer = input(decorate_line('do you have knowledge of the CeCILL-C license and accept its terms? [NO/yes] '))
		accept = answer and answer.lower() == 'yes' # require exact 'yes' answer
	if accept:
		for file in acceptance_files:
			dirname = os.path.dirname(file)
			try:
				if not os.path.exists(dirname):
					os.makedirs(dirname)
				with open(file, 'w') as f:
					f.write(acceptance_text)
			except:
				accept = False
			else:
				accept = True
				multiline_print("acceptance stored in file: '{}'".format(file))
				break
	if not accept:
		raise LicenseError

