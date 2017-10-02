# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `multi_path_protocols` support in `parse_address`

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.config import *
import hashlib
try:
	from configparser import NoOptionError # Py3
except ImportError:
	from ConfigParser import NoOptionError # Py2


def get_client_name(repository, config={}):
	"""
	Read client name from config or fall back to default.

	Arguments:

		repository (str): repository name.

		config (dict): option-value configuration dictionnary.

	Returns:

		str: client name.
	"""
	try:
		return config.pop('clientname')
	except KeyError:
		try:
			import socket
			hostname = socket.gethostname()
		except:
			hostname = None
		else:
			if hostname in ['localhost']:
				hostname = None
		if hostname:
			return hostname
		else:
			return repository


def parse_section(config, repository, logger):
	"""
	Make relay backend and parse related options.

	Arguments:

		config (ConfigParser): configuration object.

		repository (str): configuration section.

		logger (Logger): logger.

	Returns:

		(escale.relay.AbstractRelay, dict): relay class and dictionnary of parameters.
	"""
	# moved from escale.base.launcher
	# parse config
	args = parse_fields(config, repository, fields, logger)
	args['config'] = parse_others(config, repository, exclude=fields)
	# client name
	args['clientname'] = get_client_name(repository, args)
	# remote repository
	if 'address' not in args:
		# filepath-based protocols can define the relay path in the 'directory' field
		# instead of 'address' provided that the path is absolute.
		# Force this path to be in 'address' so that it will be passed to the relay 
		# backend as first input argument.
		try:
			if os.path.isabs(os.path.expanduser(args['directory'])):
				args['address'] = args.pop('directory')
		except KeyError: # 'directory' not defined
			pass
	missing = None
	try:
		_protocol, args['address'], _port, _directory = parse_address(args['address'])
	except KeyError:
		msg = 'no address defined'
		logger.error(msg)
		raise KeyError(msg)
	try:
		protocol = config.get(repository, 'protocol')
	except NoOptionError:
		protocol = _protocol
	if protocol:
		args['protocol'] = protocol
	else:
		msg = 'no protocol defined'
		logger.error(msg)
		raise KeyError(msg)
	if _port:
		if 'port' in args:
			if args['port'] != port:
					logger.debug('conflicting port values: {}, {}'.format(port, args['port']))
		else:
			args['port'] = _port
	if _directory:
		if 'directory' in args:
			args['directory'] = os.path.join(args['directory'], _directory)
		else:
			args['directory'] = _directory
	# get credential
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
	# parse encryption algorithm and passphrase
	if 'passphrase' in args and os.path.isfile(args['passphrase']):
		with open(args['passphrase'], 'rb') as f:
			args['passphrase'] = f.read()
	if 'encryption' in args:
		import escale.encryption as encryption
		if isinstance(args['encryption'], bool):
			if args['encryption']:
				cipher = encryption.by_cipher('fernet')
			else:
				cipher = None
		elif args['encryption'].startswith('native'):
			try:
				# pass the `passphrase` option to the relay backend
				args['config']['passphrase'] = args.pop('passphrase')
			except KeyError:
				pass
			cipher = None
		else:
			try:
				cipher = encryption.by_cipher(args['encryption'])
			except KeyError:
				cipher = None
				if not args['encryption'].startswith('native'):
					msg = "unsupported encryption algorithm '{}'".format(args['encryption'])
					logger.warning(msg)
					# do not let the user send plain data if she requested encryption:
					raise ValueError(msg)
		if cipher is not None and 'passphrase' not in args:
			cipher = None
			msg = 'missing passphrase; cannot encrypt'
			logger.warning(msg)
			# again, do not let the user send plain data if she requested encryption:
			raise ValueError(msg)
		delegate_encryption = False#args.get('index', False)
		if delegate_encryption or cipher is None:
			del args['encryption']
		if cipher is not None:
			_cipher = cipher(args['passphrase'])
			if delegate_encryption:
				args['config']['encryption'] = _cipher
			else:
				args['encryption'] = _cipher
	import escale.relay as relay
	relay_class = relay.by_protocol(args['protocol'], logger=logger,
		**{a:v for a,v in args.items() if a!='protocol'})
	return (relay_class, args)


def parse_address(addr, multi_path_protocols=[]):
	"""
	Parse host addresses or paths.

	Arguments:

		addr (str): host address.

		multi_path_protocols (list): list of *multi-path* protocols.

	Returns:

		(str, str, str, str): (protocol, address, port, path)

	Addresses can have multiple formats:

	* ``file://absolutepath``
	* ``protocol://servername[:port][/relativepath]``

	Note that ``absolutepath`` must start with *'/'* or *'~/'* to be identified
	as an absolute path.

	``absolutepath`` and ``servername`` are returned as second argument and 
	``relativepath`` as fourth output argument.

	*new in 0.5:* `multi_path_protocols`; moved from :mod:`escale.base.config`

	*multi-path* protocols admit paths such as:

	* ``protocol``
	* ``protocol://relativepath`` where ``relativepath`` is returned as path
	* ``protocol://absolutepath`` where ``absolutepath`` is returned as address
	* ``protocol://absolutepath//relativepath``

	Note that ``absolutepath`` must start with *'/'* or *'~/'* to be identified
	as an absolute path.

	Similarly ``relativepath`` should not start with any of *'/'* or *'~/'*.

	Example *multi-path* address:
	::

		googledrive:///home/user/MyGoogleDrive//Escale repository

	where ``/home/user/MyGoogleDrive`` is the path of the "locally-mounted"
	storage space and ``Escale repository`` is the directory that Escale will 
	use for synchronization.

	The above example can be parsed as expected if *'googledrive'* is provided
	in the `multi_path_protocols` input argument.
	"""
	try:
		protocol, addr = addr.split('://')
	except ValueError:
		addr = os.path.expanduser(addr)
		if os.path.isabs(addr):
			return (None, addr, None, None) # stop here
		elif addr in multi_path_protocols:
			protocol = addr
			return (protocol, None, None, None) # stop here
		protocol = None
	else:
		addr = os.path.expanduser(addr)
		if protocol in multi_path_protocols:
			if os.path.isabs(addr):
				try:
					addr, path = addr.split('//')
				except ValueError:
					path = None
			else:
				path = addr
				addr = None
			return (protocol, addr, None, path)
		elif os.path.isabs(addr):
			# 'file'-like protocol
			return (protocol, addr, None, None) # path is returned as second argument
	try:
		addr, path = addr.split('/', 1)
	except ValueError:
		path = None
	try:
		addr, port = addr.split(':')
	except ValueError:
		port = None
	return (protocol, addr, port, path)


def get_dist_file(default_dirs={}, filename=None,
		config=None, section=None, options=None):
	"""
	Get path of "distribution" files such as caches and locks.

	Arguments:

		default_dirs (dict): mapping configuration filepath -> distribution filepath.

		filename (str): basename.

		config (ConfigParser or str): configuration filepath or object.

		section (str): repository name.

		options (str or tuple or list): configuration option(s).

	Returns:

		str: filepath.

	*new in 0.5:* moved from :mod:`escale.base.config`

	The "dist" directory is determined from the configuration object if any,
	or from the configuration filepath combined with the `default_dirs` mapping.

	If `filename` is not provided, it is derived from the basename of the 
	configuration file.
	"""
	if config is None:
		config, cfg_file, _ = parse_cfg()
	elif isinstance(config, ConfigParser):
		cfg_file = config.filename
	else:
		cfg_file = config
		config = None
	undefined = True
	dist_dir, cfg_basename = os.path.split(cfg_file)
	if not dist_dir:
		dist_dir = os.getcwd()
	if options and config is not None:
		if section is None:
			section = default_section
		if not isinstance(options, (tuple, list)):
			options = [ options ]
		found = False
		for option in options:
			try:
				dist_dir = getpath(config, section, option)
			except NoOptionError:
				pass
			else:
				found = True
				break
		if found:
			if not os.path.isabs(dist_dir):
				raise ValueError("'{}' should be absolute path".format(option))
			undefined = False
	if undefined:
		for cfg_dir in default_dirs:
			if cfg_file.startswith(cfg_dir):
				dist_dir = default_dirs[cfg_dir]
				break
	if not filename:
		filename, _ = os.path.splitext(cfg_basename)
	dist_file = os.path.join(dist_dir, filename)
	if not os.path.isdir(dist_dir):
		if os.path.exists(dist_dir):
			raise OSError("resource '{}' is not a directory".format(dist_dir))
		os.makedirs(dist_dir)
	return dist_file


def get_pid_file(config=None):
	"""
	Get the location of the pid (process id) file.

	Arguments:

		config (ConfigParser): configuration object or filepath.

	Returns:

		str: path to pid file.

	*new in 0.5:* moved from :mod:`escale.base.config`
	"""
	pid_file = get_dist_file(default_run_dirs, config=config)
	if not pid_file.endswith('.pid'):
		pid_file += '.pid'
	return pid_file


def get_cache_file(config=None, section=None, prefix='', previously=None):
	"""
	Get the corresponding persistent data location for a given configuration 
	file and section.

	Arguments:

		config (ConfigParser): configuration object or filepath.

		section (str): section/repository name.

		prefix (str): prefixes the basename of the returned path.

		previously (str): former section/repository name if it has been renamed.

	Returns:

		str: path to persistent data location.

	*new in 0.5:* moved from :mod:`escale.base.config`
	"""
	cache_option = ['cache', 'cache dir']
	if config is None:
		config, _, _ = parse_cfg()
	elif not isinstance(config, ConfigParser): # basestring
		config, _, _ = parse_cfg(config)
	if section is None:
		section = config.sections()
		if section[1:]:
			raise ValueError("several sections were found in '{}'; 'section' should be defined".format(config.filename))
		section = section[0]
	cache_dir = get_dist_file(default_cache_dirs, config=config, section=section,
			options=cache_option)
	if PYTHON_VERSION == 3:
		if isinstance(section, str):
			section = section.encode('utf-8')
		if isinstance(previously, str):
			previously = previously.encode('utf-8')
	cache_file = os.path.join(cache_dir,
			prefix + asstr(hashlib.sha224(section).hexdigest()))
	if previously:
		previous_cache = os.path.join(cache_dir,
				prefix + asstr(hashlib.sha224(previously).hexdigest()))
		if os.path.exists(previous_cache) and not os.path.exists(cache_file):
			os.rename(previous_cache, cache_file)
	return cache_file
