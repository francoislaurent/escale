
try:
	from configparser import ConfigParser, NoOptionError
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser
	NoOptionError = cp.NoOptionError
import argparse
import sys
import os

import logging, logging.config, logging.handlers
from multiprocessing import Process, Queue
import threading

from syncacre.base import *
from syncacre.log import *
import syncacre.relay as relay
from syncacre.manager import Manager
import syncacre.encryption as encryption




# fields expected in configuration files
fields = dict(path=('path', ['local path', 'path']), \
	address=['relay address', 'remote address', 'host address', 'address'], \
	directory=['relay dir', 'remote dir', 'host dir', 'dir', 'relay directory', 'remote directory', 'host directory', 'directory'], \
	port=['relay port', 'remote port', 'host port', 'port'], \
	username=['relay user', 'remote user', 'host user', 'auth user', 'user'], \
	password=(('path', 'str'), ['password', 'secret', 'secret file', 'secrets file', 'credential', 'credentials']), \
	refresh=('float', ['refresh']), \
	timestamp=(('bool', 'str'), ['modification time', 'timestamp', 'mtime']), \
	clientname=['client', 'client name'], \
	encryption=(('bool', 'str'), ['encryption']), \
	passphrase=(('path', 'str'), ['passphrase', 'key']))


def getpath(config, section, attr):
	path = config.get(section, attr)
	if path[0] == '~':
		path = os.path.expanduser(path)
	if os.path.isdir(os.path.dirname(path)):
		return path
	else:
		raise ValueError


def getter(_type='str'):
	"""
	Config getter.

	Arguments:

		_type (type): either ``bool``, ``int``, ``float`` or ``str``.

	Returns:

		function: getter(config (ConfigParser), section (str), field (str))

	"""
	return dict(
			bool =	ConfigParser.getboolean,
			int =	ConfigParser.getint,
			float =	ConfigParser.getfloat,
			str =	ConfigParser.get,
			path =	getpath
		)[_type]


def parse_field(attrs, getters, config, config_section, logger):
	for attr in attrs:
		option = True
		for get in getters:
			try:
				return get(config, config_section, attr)
			except NoOptionError:
				option = False
				break
			except ValueError:
				pass
		if option:
			logger.warning("wrong format for attribute '%s'", attr)
	return None


def parse_cfg(args, msgs):
	cfg_file = args['config']
	if cfg_file:
		if not os.path.isfile(cfg_file):
			raise IOError('file not found: {}'.format(cfg_file))
	else:
		candidates = [os.path.expanduser('~/.config/syncacre/syncacre.conf'), \
			os.path.expanduser('~/.syncacre/syncacre.conf'), \
			'/etc/syncacre.conf', \
			None]
		for cfg_file in candidates:
			if cfg_file and os.path.isfile(cfg_file):
				break
		if not cfg_file:
			raise IOError('cannot find a valid configuration file')
	with open(cfg_file, 'r') as f:
		while True:
			line = f.readline()
			stripped = line.strip()
			if stripped and any([ stripped[0] == s for s in '#;' ]):
				stripped = ''
			if stripped:
				break
		if not line.startswith('[{}]'.format(default_section)):
			line = "[{}]\n{}".format(default_section, line)
		raw_cfg = "{}{}".format(line, f.read())
	if PYTHON_VERSION == 3:
		config = ConfigParser(default_section=default_section)
		config.read_string(raw_cfg, source=cfg_file)
	elif PYTHON_VERSION == 2:
		assert default_section == 'DEFAULT'
		config = ConfigParser()
		import io
		config.readfp(io.BytesIO(raw_cfg))
	return (cfg_file, config, msgs)



def syncacre(config, repository, handler=None):
	"""
	Reads the section related to a repository in a loaded configuration object and spawns a 
	:class:`~syncacre.manager.Manager` for that repository.
	"""
	logger = logging.getLogger(log_root).getChild(repository)
	if handler is not None:
		logger.propagate = False
		logger.setLevel(logging.DEBUG)
		logger.addHandler(handler)
	args = {}
	for field, attrs in fields.items():
		if isinstance(attrs, tuple):
			types, attrs = attrs
			if isinstance(types, str):
				types = (types,)
			getters = [ getter(t) for t in types ]
		else:
			getters = [ getter() ]
		value = parse_field(attrs, getters, config, repository, logger)
		if value is not None:
			args[field] = value
	if 'password' in args and os.path.isfile(args['password']):
		with open(args['password'], 'r') as f:
			content = f.readlines()
		content = [ line[:-1] if line[-1] == "\n" else line for line in content ]
		if 'username' in args:
			if not content[1:]:
				args['password'] = content[0]
			else:
				ok = False
				for line in content:
					if line.startswith(args['username']):
						args['password'] = line[len(args['username'])+1:]
						ok = True
						break
				if not ok:
					logger.error("cannot read password for user '%s' from file '%s'", args['username'], args[ 'password'])
					del args['password']
		else:
			try:
				args['username'], args['password'] = content[0].split(':', 1)
			except ValueError:
				logger.error("cannot read login information from credential file '%s'", args['password'])
				del args['password']
	#
	try:
		write_only = config.getboolean(repository, 'write only')
		if write_only:
			args['mode'] = 'download'
	except NoOptionError:
		pass
	try:
		read_only = config.getboolean(repository, 'read only')
		if read_only:
			if 'mode' in args: # write_only is also True
				logger.warning('both read only and write only; cannot determine mode')
				return
			else:
				args['mode'] = 'upload'
	except NoOptionError:
		pass
	# parse encryption passphrase
	if 'passphrase' in args and os.path.isfile(args['passphrase']):
		with open(args['passphrase'], 'rb') as f:
			args['passphrase'] = f.read()
	if 'encryption' in args:
		if isinstance(args['encryption'], bool):
			if args['encryption']:
				cipher = encryption.Fernet
			else:
				cipher = None
		else:
			try:
				cipher = encryption.by_cipher(args['encryption'].lower())
			except KeyError:
				cipher = None
				msg = ("unsupported encryption algorithm '%s'", args['encryption'])
				logger.warning(*msg)
				# do not let the user send plain data if she requested encryption:
				raise ValueError(*msg)
		if cipher is not None and 'passphrase' not in args:
			cipher = None
			msg = ('missing passphrase; cannot encrypt',)
			logger.warning(*msg)
			# again, do not let the user send plain data if she requested encryption:
			raise ValueError(*msg)
		if cipher is None:
			del args['encryption']
		else:
			args['encryption'] = cipher(args['passphrase'])
	# relay type
	try:
		protocol = config.get(repository, 'protocol')
	except NoOptionError:
		protocol = args['address'].split(':')[0] # crashes if no colon found
	#if PYTHON_VERSION == 3:
	#	args['config'] = config[repository]
	#elif PYTHON_VERSION == 2:
	#	args['config'] = (config, repository)
	manager = Manager(relay.by_protocol(protocol), protocol=protocol, logger=logger, **args)
	manager.run()




def main(**args):
	"""
	Parses a configuration file and calls `syncacre` on each declared repository.
	"""
	# initialize the first series of logs; they will be flushed once the logger will be set
	msgs = []
	# parse the config file(s)
	cfg_file, config, msgs = parse_cfg(args, msgs)
	# configure logger
	logger, msgs = set_logger(cfg_file, config, args, msgs)
	# flush messages
	for msg in msgs:
		if isinstance(msg, tuple):
			if isinstance(msg[0], str):
				logger.warning(*msg)
			else: # msg[0] is log level
				logger.log(*msg)
		else:
			logger.warning(msg)
	# handle -d option
	if not args['daemon']:
		try:
			args['daemon'] = config.getboolean(default_section, 'daemon')
		except NoOptionError:
			pass
	if args['daemon']:
		try:
			import daemon
		except ImportError:
			logger.warning("the 'python-daemon' library is not installed; cannot daemonize")
			logger.info('you can get it with:')
			logger.info('     pip install python-daemon')
			logger.info('alternatively, you can run syncacre with nohup and &:')
			logger.info('     nohup python -m syncacre -c my-conf-file &')
			args['daemon'] = False
	# spawn syncacre subprocess(es)
	if args['daemon']:
		pwd = os.getcwd()
		with daemon.DaemonContext(working_directory=pwd):
			syncacre_launcher(config)
	else:
		syncacre_launcher(config)
	return 0


def syncacre_launcher(config, daemon=None):
	sections = config.sections()
	if sections[1:]: # if multiple sections
		if PYTHON_VERSION == 3:
			queue = Queue()
			listener = QueueListener(queue)
			handler = logging.handlers.QueueHandler(queue)
		elif PYTHON_VERSION == 2:
			import syncacre.log.socket as socket
			conn = ('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
			listener = socket.SocketListener(*conn)
			handler = logging.handlers.SocketHandler(*conn)
		# logger
		logger_thread = threading.Thread(target=listener.listen)
		logger_thread.start()
		# syncacre subprocesses
		workers = []
		for section in config.sections():
			worker = Process(target=syncacre,
				name='{}.{}'.format(log_root, section),
				args=(config, section, handler))
			if daemon is not None:
				worker.daemon = daemon
			workers.append(worker)
			worker.start()
		# wait for everyone to terminate
		try:
			for worker in workers:
				worker.join()
		except KeyboardInterrupt:
			for worker in workers:
				worker.terminate()
		listener.abort()
		logger_thread.join()
	else:
		syncacre(config, sections[0])




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

