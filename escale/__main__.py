# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#     * -r option and `keepalive` function

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import argparse
import sys
import os

import logging
import time

from escale.base import *
from escale.base.launcher import *
from escale.cli.config import *
from escale.cli.license import *
from escale import __version__


auto_restart_default = 60


def main():
	"""
	Delegate to `escale_launcher` in a daemon process or in the mean thread.
	"""
	# command-line
	parser = argparse.ArgumentParser(prog=PROGRAM_NAME, argument_default=argparse.SUPPRESS, \
		description='Escale - Client-to-client synchronization based on external relay storage', \
		epilog='See also escalectl')
	parser.add_argument('-c', '--config', type=str, metavar='FILE', help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon')
	import_metavar = 'FILE'
	parser.add_argument('--interactive', action='store_true',
			help='assists with configuring escale')
	parser.add_argument('--import', type=str, metavar=import_metavar,
			help='imports a configuration file')
	parser.add_argument('-i', type=str, nargs='?', metavar=import_metavar,
			help='shorthand for --import if followed by {}, or --interactive otherwise'.format(import_metavar))
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently [deprecated]')
	parser.add_argument('-r', '--auto-restart', type=int, nargs='?', metavar='TIME', help='restart {} when it crashed; can specify a time interval in seconds before restart [default {}]'.format(PROGRAM_NAME, auto_restart_default))
	parser.add_argument('-y', '--accept-license', action='store_true', help='skip the license acceptance step at first startup and agree with the terms of the license')
	args = parser.parse_args()
	# license acceptance
	try:
		check_license_acceptance(args.__dict__.get('accept_license', False))
	except LicenseError as e:
		print(str(e))
		return
	args = args.__dict__
	# reverse the changes introduced by ``argument_default=argparse.SUPPRESS``
	if 'config' not in args:
		args['config'] = None
	if 'i' in args:
		if args['i']:
			# -i FILE means --import FILE
			translation = 'import'
			value = args['i']
		else:
			translation = 'interactive'
			value = True
		if translation in args:
			print("'-i' and '--{}' conflict".format(translation))
			return
		else:
			args[translation] = value
		del args['i']
	if 'interactive' not in args:
		args['interactive'] = False
	if 'disable_proxy' not in args:
		args['disable_proxy'] = False
	if 'daemon' not in args:
		args['daemon'] = False
	if 'quiet' not in args:
		args['quiet'] = False
	if 'auto_restart' not in args:
		args['auto_restart'] = False
	elif args['auto_restart'] is None:
		args['auto_restart'] = auto_restart_default
	if 'accept_license' in args:
		del args['accept_license']
	# initialize the pending logs
	# they will be flushed by `escale_launcher` once the logger will be set
	msgs = []
	# import configuration file
	if 'import' in args:
		cfg_file = os.path.expanduser(args['import'])
		if not os.path.isfile(cfg_file):
			print("cannot find file '{}'".format(cfg_file))
			return
		try:
			extra_config, _, _ = parse_cfg(cfg_file)
		except Exception as e:
			print("corrupted file '{}':".format(cfg_file))
			print(e)
			return
		if not extra_config.sections():
			print("not any section in '{}'".format(cfg_file))
			return
		dirname, basename = os.path.split(cfg_file)
		try:
			existing_config, destination, _ = parse_cfg()
		except IOError: # cannot find a valid configuration file
			destination = default_conf_files[0]
			copyfile(cfg_file, destination)
		else:
			# merge extra configuration into existing one
			existing_sections = [ s for s in extra_config.sections()
					if existing_config.has_section(s) ]
			if existing_sections:
				raise NotImplementedError("section '{}' already exists".format(existing_sections[0]))
			if extra_config.defaults(): # has defaults?
				raise NotImplementedError("file '{}' has global settings".format(cfg_file))
			with open(cfg_file, 'r') as fi:
				with open(destination, 'a') as fo:
					fo.write(fi.read())
		return
	# assist the user in configuring escale
	if args['interactive']:
		try:
			msgs = edit_config(args['config'], msgs)
		except ExpressInterrupt:
			# suppress output
			pass
		return # new in 0.5rc2
	# if auto-restart, delegate to `keepalive`
	if args['auto_restart'] and not args['daemon']:
		keep_alive(sys.argv[0], args['auto_restart'], *sys.argv[1:])
		return
	# welcome message
	msgs.append((logging.INFO, "running version %s", __version__))
	# handle -d option
	if args['daemon']:
		try:
			import daemon
		except ImportError:
			msgs.append((logging.WARNING, "the 'python-daemon' library is not installed; cannot daemonize"))
			msgs.append((logging.INFO, 'you can add it to your Python distribution with:'))
			msgs.append((logging.INFO, '     pip install python-daemon'))
			msgs.append((logging.INFO, "alternatively, you can run %s with 'nohup':", PROGRAM_NAME))
			msgs.append((logging.INFO, '     nohup %s &', PROGRAM_NAME))
			args['daemon'] = False
	# handle the other commandline options
	launcher_args = (args['config'], msgs, not args['quiet'], args['auto_restart'])
	# spawn escale subprocess(es)
	if args['daemon']:
		with daemon.DaemonContext(working_directory=os.getcwd()):
			escale_launcher(*launcher_args)
	else:
		escale_launcher(*launcher_args)



def keep_alive(escale, interval, *argv):
	"""
	Run Escale in another Python environment and restart on exit.
	"""
	import subprocess
	if interval is None:
		interval = auto_restart_default
	argv = list(argv)
	python = sys.executable
	if python is None:
		if PYTHON_VERSION == 3:
			python = 'python3'
		else:
			python = 'python'
	try:
		i = argv.index('-r')
	except ValueError:
		pass
	else:
		try:
			int(argv[i+1])
		except (IndexError, ValueError):
			pass
		else:
			del argv[i+1]
		del argv[i]
	cmd = '{} -m {}' + ' {}' * len(argv)
	cmd = cmd.format(python, PROGRAM_NAME, *argv)
	while True:
		print("running '{}'".format(cmd))
		subprocess.call([python, '-m', PROGRAM_NAME] + argv)
		print('{} is going to restart in {} seconds'.format(PROGRAM_NAME, interval))
		print('   hit Ctrl+C now to prevent restart')
		try:
			time.sleep(interval)
			continue
		except KeyboardInterrupt:
			print(' shutting down') # ^C may appear on the command-line, hence the initial space
			break


if __name__ == '__main__':
	main()
	sys.exit(0)

