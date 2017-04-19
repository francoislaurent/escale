
import argparse
import sys
import os

import logging

from syncacre.base import *


def main(**args):
	"""
	Delegates to `syncacre_launcher` in a daemon process or in the mean thread.
	"""
	# initialize the pending logs
	# they will be flushed by `syncacre_launcher` once the logger will be set
	msgs = []
	# potential fix for issue #14
	msgs.append((logging.DEBUG, 'special version for issue #14 (2)'))
	if 'https_proxy' in os.environ:
		msgs.append((logging.DEBUG, "'https_proxy' environment variable was set to '%s'; unsetting it", os.environ['https_proxy']))
		del os.environ['https_proxy']
	# handle -d option
	if args['daemon']:
		try:
			import daemon
		except ImportError:
			msgs.append((logging.WARNING, "the 'python-daemon' library is not installed; cannot daemonize"))
			msgs.append((logging.INFO, 'you can get it with:'))
			msgs.append((logging.INFO, '     pip install python-daemon'))
			msgs.append((logging.INFO, 'alternatively, you can run syncacre with nohup and &:'))
			msgs.append((logging.INFO, '     nohup python -m syncacre -c my-conf-file &'))
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
	parser = argparse.ArgumentParser(prog='syncacre', \
		description='SynCÀCRe - Client-to-client synchronization based on external relay storage', \
		epilog='See also https://github.com/francoislaurent/syncacre')
	parser.add_argument('-c', '--config', type=str, help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon')
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently')

	args = parser.parse_args()
	exit_code = main(**args.__dict__)
	sys.exit(exit_code)

