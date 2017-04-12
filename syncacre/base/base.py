
import logging, logging.handlers, logging.config
from multiprocessing import Process, Queue
import threading
try:
	from configparser import NoOptionError
except ImportError:
	from ConfigParser import NoOptionError

from .essential import *
from .config import *
from syncacre.log import *
import syncacre.relay as relay
from syncacre.manager import Manager
import syncacre.encryption as encryption



def syncacre(config, repository, handler=None):
	"""
	Reads the section related to a repository in a loaded configuration object and runs a 
	:class:`~syncacre.manager.Manager` for that repository.

	Arguments:

		config (ConfigParser): configuration object.

		repository (str): configuration section name or, equivalently, client name.

		handler (None or log handler)
	"""
	logger = logging.getLogger(log_root).getChild(repository)
	logger.setLevel(logging.DEBUG)
	if handler is not None:
		logger.propagate = False
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



def syncacre_launcher(cfg_file, msgs=[], verbosity=logging.NOTSET, daemon=None):
	"""
	Parses a configuration file, sets the logger and launches the clients in separate subprocesses.

	Arguments:

		cfg_file (str): path to a configuration file.

		msgs (list): list of pending messages (`str` or `tuple`).

		verbosity (bool or int): verbosity level.

		daemon (bool): default value should not be changed.

	"""
	# parse the config file
	config, cfg_file, msgs = parse_cfg(cfg_file, msgs)
	# configure logger
	logger, msgs = set_logger(config, cfg_file, verbosity, msgs)
	# flush messages
	for msg in msgs:
		if isinstance(msg, tuple):
			if isinstance(msg[0], str):
				logger.warning(*msg)
			else: # msg[0] is log level
				logger.log(*msg)
		else:
			logger.warning(msg)
	# launch each client
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

