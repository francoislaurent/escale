# -*- coding: utf-8 -*-

import argparse
import sys
import os

import logging

from syncacre.base import *
from syncacre.cli.config import *
from syncacre import __version__


def main(**args):
	"""
	Delegates to `syncacre_launcher` in a daemon process or in the mean thread.
	"""
	# initialize the pending logs
	# they will be flushed by `syncacre_launcher` once the logger will be set
	msgs = []
	# assist the user in configuring syncacre
	if args['interactive']:
		msgs = add_section(args['config'], msgs)
	# welcome message
	msgs.append((logging.INFO, "running version %s", __version__))
	# proxy disabling is deprecated; it was introduced as a possible fix for issue #14
	if args['disable_proxy'] and 'HTTPS_PROXY' in os.environ:
		msgs.append((logging.WARNING, "'-p' option is deprecated; support will be dropped soon"))
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
			msgs.append((logging.INFO, 'alternatively, you can run %S with `nohup` and `&`:', SYNCACRE_NAME))
			msgs.append((logging.INFO, '     nohup python -m syncacre &'))
			args['daemon'] = False
	# handle the other commandline options
	launcher_args = (args['config'], msgs, not args['quiet'])
	# spawn syncacre subprocess(es)
	if args['daemon']:
		pwd = os.getcwd()
		with daemon.DaemonContext(working_directory=pwd):
			syncacre_launcher(*launcher_args)
	else:
		syncacre_launcher(*launcher_args)
	return 0



if __name__ == '__main__':

	parser = argparse.ArgumentParser(prog=SYNCACRE_NAME, \
		description='SynCÀCRe - Client-to-client synchronization based on external relay storage', \
		epilog='See also https://github.com/francoislaurent/syncacre')
	parser.add_argument('-c', '--config', type=str, help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon')
	parser.add_argument('-i', '--interactive', action='store_true', help='asks questions to fill in an extra section in the configuration file')
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently')
	parser.add_argument('-p', '--disable-proxy', action='store_true', help='disables proxies [deprecated]')

	args = parser.parse_args()
	exit_code = main(**args.__dict__)
	sys.exit(exit_code)

