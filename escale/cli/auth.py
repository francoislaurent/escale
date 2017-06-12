# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.essential import *
from getpass import *
import time

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass



def request_credential(hostname=None, username=None):
	'''
	Request credential input from the command-line.

	Arguments:

		hostname (str): hostname of the remote machine that requests credential.

		username (bool or str): username, if only the password is to be requested.
			If no username information is available and only a password is desired, 
			can be any non-string value evaluating to ``True``.

	Returns:

		str or (str, str): password, if only a password is requested, or (username, password).
	'''
	if isinstance(username, (binary_type, text_type)):
		_user = username
		username = False
	else:
		_user = ''
	time.sleep(2)
	try:
		if not username:
			if hostname:
				request = u"username for '{}': ".format(hostname)
			else:
				request = 'username: '
			while not _user:
				_user = input(request)
		if _user:
			if hostname:
				request = u"password for '{}@{}': ".format(_user, hostname)
			else:
				request = u"password for '{}': ".format(_user)
		else:
			request = 'password: '
		_pass = ''
		while not _pass:
			_pass = getpass(request)
	except EOFError as e:
		# e.args is ('EOF when reading a line',)
		e.args = ('connection to console lost',)
		raise e
	if username:
		credential = _pass
	else:
		credential = (_user, _pass)
	return credential


