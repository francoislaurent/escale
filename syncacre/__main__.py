# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

# Copyright (c) 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contribution:
#     * -p option (initial support, without `try` block)
#     * -r option and `keepalive` function

import argparse
import sys
import os

import logging
import time

from syncacre.base import *
from syncacre.cli.config import *
from syncacre import __version__

auto_restart_default = 60

def main(**args):
	"""
	Delegates to `syncacre_launcher` in a daemon process or in the mean thread.
	"""
	# reverse the changes introduced by ``argument_default=argparse.SUPPRESS`` addition
	if 'config' not in args:
		args['config'] = None
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
	# initialize the pending logs
	# they will be flushed by `syncacre_launcher` once the logger will be set
	msgs = []
	# assist the user in configuring syncacre
	if args['interactive']:
		msgs = add_section(args['config'], msgs)
	# welcome message
	msgs.append((logging.INFO, "running version %s", __version__))
	# proxy disabling is deprecated; it was introduced as a possible fix for issue #14
	if args['disable_proxy']:
		msgs.append((logging.WARNING, "'-p' option is deprecated; support will be dropped soon"))
		if 'HTTPS_PROXY' in os.environ: # never tested
			msgs.append((logging.DEBUG, "'HTTPS_PROXY' environment variable was set to '%s'; unsetting it", os.environ['HTTPS_PROXY']))
			del os.environ['HTTPS_PROXY']
	# handle -d option
	if args['daemon']:
		try:
			import daemon
		except ImportError:
			msgs.append((logging.WARNING, "the 'python-daemon' library is not installed; cannot daemonize"))
			msgs.append((logging.INFO, 'you can add it to your Python distribution with:'))
			msgs.append((logging.INFO, '     pip install python-daemon'))
			msgs.append((logging.INFO, 'alternatively, you can run %s with `nohup` and `&`:', PROGRAM_NAME))
			msgs.append((logging.INFO, '     nohup python -m syncacre &'))
			args['daemon'] = False
	# handle the other commandline options
	launcher_args = (args['config'], msgs, not args['quiet'], args['auto_restart'])
	# spawn syncacre subprocess(es)
	if args['daemon']:
		with daemon.DaemonContext(working_directory=os.getcwd()):
			syncacre_launcher(*launcher_args)
	else:
		syncacre_launcher(*launcher_args)
	return 0



def keepalive(syncacre, interval, *argv):
	"""
	Run syncacre in another Python environment.
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
	cmd = '{} -m syncacre' + ' {}' * len(argv)
	cmd = cmd.format(python, *argv)
	while True:
		print("running '{}'".format(cmd))
		subprocess.call([python, '-m', 'syncacre'] + argv)
		print('syncacre is going to restart in {} seconds'.format(interval))
		print('   hit Ctrl+C now to prevent restart')
		try:
			time.sleep(interval)
			continue
		except KeyboardInterrupt:
			print(' shutting down') # ^C may appear on the command-line, hence the initial space
			break
	return 0



if __name__ == '__main__':

	parser = argparse.ArgumentParser(prog=PROGRAM_NAME, argument_default=argparse.SUPPRESS, \
		description='SynCÀCRe - Client-to-client synchronization based on external relay storage', \
		epilog='See also https://github.com/francoislaurent/syncacre')
	parser.add_argument('-c', '--config', type=str, help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon')
	parser.add_argument('-i', '--interactive', action='store_true', help='asks questions to fill in an extra section in the configuration file')
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently')
	parser.add_argument('-p', '--disable-proxy', action='store_true', help='disables proxies [deprecated]')
	parser.add_argument('-r', '--auto-restart', type=int, nargs='?', help='restart {} when it crashed; can specify a time interval in seconds before restart [default {}]'.format(PROGRAM_NAME, auto_restart_default))

	args = parser.parse_args()
	if hasattr(args, 'auto_restart') and not hasattr(args, 'daemon'):
		exit_code = keepalive(sys.argv[0], args.auto_restart, *sys.argv[1:])
	else:
		exit_code = main(**args.__dict__)
	sys.exit(exit_code)

