# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import PROGRAM_NAME, asstr, ExpressInterrupt
from escale.base.config import fields, parse_field, default_option
from escale.cli.config import query_field
from escale.cli.format import *
from escale.relay.generic.rclone import rclone_binary
from escale.base.subprocess import *
import os
import subprocess
try:
	from configparser import ConfigParser # Py3
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass


rclone_option = 'rclone binary'
suggested_go_path = '~/golang'


def setup(config, section, service=None):
	rclone_bin = rclone_binary(parse_field(config, section, rclone_option))
	if not rclone_bin:
		multiline_print("cannot find rclone;",
			"if you don't have it installed, leave the following field empty:")
		rclone_bin = rclone_binary(query_field(config, section, rclone_option)[1])
	if rclone_bin:
		config.set(section, rclone_option, rclone_bin)
	else:
		go_version = False
		try:
			# running arbitrary commands is not safe
			v = with_subprocess('go', 'version', error=True)
		except:
			pass
		else:
			v = asstr(v)
			if v.startswith('go version go'):
				go_version = tuple([ int(v) for v in v.split()[2][2:].split('.') ])
		if go_version and (1,6) <= go_version:
			multiline_print("the 'rclone' Go package is going to be installed")
			answer = input(decorate_line("do you want to proceed? [Y/n] "))
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
			extra_args = {'wait': True}
			# the PATH environment variable is also needed
			try:
				env['PATH'] = os.environ['PATH']
			except KeyError:
				extra_args['shell'] = True
			extra_args['env'] = env
			# install rclone
			cmd = ('go', 'get', '-u', 'github.com/ncw/rclone')
			print(' '.join(cmd))
			with_subprocess(*cmd, **extra_args)
			rclone_bin = os.path.join(go_path, 'bin', 'rclone')
			if os.path.isfile(rclone_bin):
				config.set(section, rclone_option, rclone_bin)
			else:
				raise EnvironmentError("failed to install 'rclone'")
			multiline_print("'rclone' installed")
		else:
			if go_version:
				multiline_print(
					"your version of Go is too old")
			else:
				multiline_print(
					"please install the Go toolchain and run the wizard again",
					"to set up the path of the 'rclone' command")
			multiline_print(
				"you can alternatively install a compiled version of ",
				"'rclone' following the instructions available at:",
				"https://rclone.org/install/")
	config = set_remote(config, section, service)
	return config



def set_remote(config, section, service=None, rclone_conf='~/.config/rclone/rclone.conf'):
	rclone_bin = config.get(section, rclone_option)
	if service and service.name == 'rclone':
		remote = 'remote'
	else:
		remote = section
	rclone_cfg_file = os.path.expanduser(rclone_conf)
	rclone_config = ConfigParser()
	if os.path.isfile(rclone_cfg_file):
		try:
			rclone_config.read([rclone_cfg_file])
		except Exception as e:
			print(e)
			pass
		else:
			if not rclone_config.has_section(remote):
				_, answer = query_field(config, section, 'address', \
					description="rclone \"remote\"'s name", \
					suggestion=remote)
				if answer:
					remote = answer
	if not rclone_config.has_section(remote):
		multiline_print("running 'rclone config'")
		if service and service.rclone_docs:
			multiline_print("see also: https://rclone.org/{}/".format(service.rclone_docs))
		try:
			p = subprocess.Popen((rclone_bin, 'config'))
			p.communicate()
		except ExpressInterrupt:
			raise
		except Exception as e:
			debug_print('{}'.format(e))
		else:
			existing_sections = rclone_config.sections()
			rclone_config = ConfigParser()
			rclone_config.read([rclone_cfg_file])
			new_remote = [ s for s in rclone_config.sections() \
				if s not in existing_sections ]
			if new_remote:
				remote = new_remote[0]
		multiline_print("back to {}".format(PROGRAM_NAME))
	config.set(section, default_option('address'), remote)
	return config

