# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.config import parse_field
from escale.cli.config import query_field
from escale.cli.format import *
from escale.relay.google.drive import *
from escale.base.subprocess import *
import os

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass


drive_option = 'drive binary'
suggested_go_path = '~/golang'


def setup(config, section):
	drive_bin = drive_binary(parse_field(config, section, drive_option))
	if not drive_bin:
		multiline_print("if you don't have 'drive' installed, leave it empty:")
		drive_bin = drive_binary(query_field(config, section, drive_option)[1])
	if drive_bin:
		config.set(section, drive_option, drive_bin)
	else:
		go_available = False
		try:
			# running arbitrary commands is not safe
			v = with_subprocess('go', 'version', error=True)
		except:
			pass
		else:
			go_available = v.startswith('go ')
		if go_available:
			multiline_print("the 'drive' Go package is going to be installed")
			answer = input(decorate_line("do you want to continue? [Y/n] "))
			if answer and answer[0] not in 'yY':
				raise ValueError # abort
			try:
				go_path = os.environ['GOPATH']
			except KeyError:
				multiline_print("cannot find the 'GOPATH' environment variable")
				go_path = input(decorate_line("where do you want Go packages to be installed? [{}] ".format(suggested_go_path)))
				if not go_path:
					go_path = suggested_go_path
				go_path = os.path.expanduser(go_path)
			env = {'GOPATH': go_path}
			extra_args = {}
			# the PATH environment variable is also needed
			try:
				env['PATH'] = os.environ['PATH']
			except KeyError:
				extra_args['shell'] = True
			# install drive
			with_subprocess('go', 'get', '-u', 'github.com/odeke-em/drive/drive-google',
					env=env, **extra_args)
			drive_bin = os.path.join(go_path, 'bin', 'drive-google')
			if os.path.isfile(drive_bin):
				config.set(section, drive_option, drive_bin)
			else:
				raise EnvironmentError("failed to install 'drive'")
	return config

