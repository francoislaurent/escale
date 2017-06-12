# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `ssl_version`, `verify_ssl`, `filetype`, `quota` in `fields`
#     * `_item_separator`, `getlist`, `getunit`, `storage_space_unit` (dict() statement)
#     * `list = getlist` and `number_unit = getnum` lines in `getter`
#     * `multi_path_protocols` support in `parse_address`

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from .essential import *
import os
try:
	from configparser import ConfigParser, NoOptionError # Py3
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser
	NoOptionError = cp.NoOptionError
import re # moved from syncacre.cli.config together with parse_address
import hashlib
import itertools


# configparser
default_section = 'DEFAULT' # Python2 cannot modify it

default_filename = PROGRAM_NAME + '.conf'
global_cfg_dir = '/etc'
user_cfg_dir = os.path.join(os.path.expanduser('~/.config'), PROGRAM_NAME)
user_program_dir = os.path.expanduser('~/.' + PROGRAM_NAME)
default_cfg_dirs = [ user_cfg_dir, user_program_dir, global_cfg_dir ]
default_conf_files = [ os.path.join(d, default_filename) for d in default_cfg_dirs ]

global_run_dir = '/var/run'
default_run_dirs = { user_cfg_dir: user_cfg_dir,
		user_program_dir: user_program_dir,
		global_cfg_dir: global_run_dir }

global_cache_dir = os.path.join('/var/cache', PROGRAM_NAME)
user_cache_dir = os.path.join(os.path.expanduser('~/.cache'), PROGRAM_NAME)
default_cache_dirs = { user_cfg_dir: user_cache_dir,
		user_program_dir: os.path.join(user_program_dir, 'cache'),
		global_cfg_dir: global_cache_dir }


# fields expected in configuration files
# 'directory': 'host path', 'relay path', 'remote path' added in version 0.4a3
# 'password': 'secrets file' and 'credentials' removed in version 0.4a3
# 'refresh': can be bool in version 0.4a3
# 'maintainer' added in version 0.4.1a1
# 'quota' added in version 0.4.1a2
# 'certfile' and 'keyfile' added in version 0.4.1
# 'pattern' added in version 0.4.2a4
# 'locktimeout', 'mode' and 'count' added in version 0.5
fields = dict(path=('path', ['local path', 'path']),
	address=['host address', 'relay address', 'remote address', 'address'],
	directory=['host directory', 'relay directory', 'remote directory',
		'directory', 'relay dir', 'remote dir', 'host dir', 'dir',
		'host path', 'relay path', 'remote path'],
	port=['port', 'host port', 'relay port', 'remote port'],
	username=['user', 'auth user', 'host user', 'relay user', 'remote user'],
	password=(('path', 'str'),
		['password', 'secret', 'secret file', 'credential']),
	refresh=(('bool', 'float'), ['refresh']),
	timestamp=(('bool', 'str'), ['modification time', 'timestamp', 'mtime']),
	clientname=['client name', 'client'],
	encryption=(('bool', 'str'), ['encryption']),
	passphrase=(('path', 'str'), ['passphrase', 'key']),
	push_only=('bool', ['push only', 'read only']),
	pull_only=('bool', ['pull only', 'write only']),
	ssl_version=['ssl version'],
	verify_ssl=('bool', ['verify ssl']),
	filetype=('list', ['file extension', 'file type']),
	pattern=['pattern', 'filter'],
	quota=('number_unit', ['disk quota']),
	maintainer=['maintainer', 'email'],
	certfile=('path', ['certfile', 'cert file', 'certificate']),
	keyfile=('path', ['keyfile', 'key file', 'private key']),
	locktimeout=(('bool', 'int'), ['lock timeout']),
	mode=['mode', 'synchronization mode'],
	count=('int', ['puller count', 'pullers']))


def default_option(field, all_options=False):
	"""
	Return the first option for a field declared in `fields`.
	"""
	try:
		options = fields[field]
	except KeyError:
		option = field
		options = [ option ]
	else:
		if isinstance(options, tuple):
			options = options[1]
		option = options[0]
	if all_options:
		return options
	else:
		return option

# convenient unit-to-megabyte conversion table for storage space.
# note that excessively small units like b or B are not supported,
# as well as excessively large ones like Zb, ZB.
storage_space_unit = dict(
		Kb =	0.0001220703125,
		KB =	0.0009765625,
		Mb =	0.125,
		MB =	1,
		Gb =	128,
		GB =	1024,
		Tb =	131072,
		TB =	1048576,
		Pb =	134217728,
		PB =	1073741824,
		Eb =	137438953472,
		EB =	1099511627776,
	)
# the extra units below were added in v0.4.1rc1, Copyright (c) 2017 François Laurent
for _unit in 'KMGTPE':
	storage_space_unit[_unit] = storage_space_unit[_unit+'B']
	storage_space_unit[_unit+'o'] = storage_space_unit[_unit] # latin units


def getpath(config, section, attr):
	path = config.get(section, attr)
	if path[0] == '~':
		path = os.path.expanduser(path)
	if os.path.isdir(os.path.dirname(path)):
		return path
	else:
		raise ValueError("cannot find directory '{}'".format(path))


_item_separator = ','

def getlist(config, section, attr):
	_list = [ i.strip() for i in config.get(section, attr).split(_item_separator) ]
	return [ i for i in _list if i ]


def getnum(config, section, attr):
	'''
	Getter for numbers accompanied with a unit.

	A number can be formatted as ``[0-9]+([.,][0-9]+)?`` and a unit as ``[a-zA-Z]+``.

	Arguments:

		config (ConfigParser): configuration object.

		section (str): existing configuration section.

		attr (str): existing configuration option.

	Returns:

		(float, str): numeric value and unit.
	'''
	value = config.get(section, attr)
	m = re.match(r'(?P<num>[0-9]+([.,][0-9]+)?)\s*(?P<unit>[a-zA-Z]*)', value)
	if not m:
		raise ValueError("wrong number or unit format: '{}'".format(value))
	num = float(m.group('num').replace(',', '.'))
	unit = m.group('unit')
	return (num, unit)



def getter(_type='str'):
	"""
	Config getter.

	Arguments:

		_type (str): either ``bool``, ``int``, ``float``, ``str``, ``path`` or ``list``.

	Returns:

		function: getter(config (ConfigParser), section (str), field (str))

	"""
	return dict(
			bool =	ConfigParser.getboolean,
			int =	ConfigParser.getint,
			float =	ConfigParser.getfloat,
			str =	ConfigParser.get,
			path =	getpath,
			list =	getlist,
			number_unit =	getnum,
		)[_type]


def parse_field(config, section, attrs, getters=None, logger=None):
	if not getters:
		getters = [ ConfigParser.get ]
	last_err_msg = ''
	for attr in attrs:
		option = True
		for get in getters:
			try:
				return get(config, section, attr)
			except NoOptionError:
				option = False
				break
			except ValueError as e:
				if e.args and e.args[0]:
					last_err_msg = e.args[0]
		if option:
			msg = "wrong format for attribute '{}'".format(attr)
			if logger is None:
				print("warning: "+msg)
				if last_err_msg:
					print(last_err_msg)
			else:
				logger.warning(msg)
				if last_err_msg:
					logger.warning(last_err_msg)
			return config.get(section, attr)
	return None


def parse_fields(config, section, fields, logger=None):
	'''
	Extract several options from a configuration object.

	Arguments:

		config (ConfigParser): configuration object.

		section (str): existing section in `config`.

		fields (dict): option definition similar to the global `~escale.base.config.fields`.

		logger (Logger): logger.

	Returns:

		dict: dictionnary whose keys are borrowed from those in fields and values are the parsed 
		option values.
	'''
	args = {}
	for field, attrs in fields.items():
		if isinstance(attrs, tuple):
			types, attrs = attrs
			if isinstance(types, str):
				types = (types,)
			getters = [ getter(t) for t in types ]
		else:
			getters = [ getter() ]
		value = parse_field(config, section, attrs, getters, logger)
		if value is not None:
			args[field] = value
	return args


def parse_others(config, section, exclude=fields):
	'''
	Extract options that are NOT listed in `exclude`.

	Arguments:

		config (ConfigParser): configuration object.

		section (str): existing section in `config`.

		exclude (list or dict): option list or option definition similar to the global 
			`~escale.base.config.fields`.
	
	Returns:

		dict: dictionnary with options as keys and the corresponding value as value.
	'''
	args = {}
	if isinstance(exclude, dict):
		fields = exclude
		exclude = []
		for options in fields.values():
			if isinstance(options, tuple):
				options = options[1]
			if not isinstance(options, list):
				options = [ options ]
			exclude.append(options)
		exclude = itertools.chain(*exclude)
	options = dict(config.items(section))
	for option in exclude:
		options.pop(option, None)
	return options


def parse_cfg(cfg_file='', msgs=[], new=False):
	'''
	Parse a configuration file.

	Arguments:

		cfg_file (str): path to a configuration file.

		msgs (list): list of pending messages.

		new (bool): if ``True`` and `cfg_file` does not exist, create the file.

	Returns:

		(ConfigParser, str, list):
		first argument is the parsed configuration,
		second argument is the corresponding file path,
		third argument is the list of pending messages.

	*new in version 0.5:* the returned `ConfigParser` object contains an extra
		attribute `filename` which value equals to the second returned argument.

	'''
	if cfg_file:
		err_msg_if_missing = 'file not found: {}'.format(cfg_file)
	else:
		err_msg_if_missing = 'cannot find a valid configuration file'
		candidates = default_conf_files + [None]
		for cfg_file in candidates:
			if cfg_file and os.path.isfile(cfg_file):
				break
		if not cfg_file:
			try: # check if superuser
				cfg_file = default_conf_files[-1] # global conf file
				with open(cfg_file, 'a'):
					pass
			except IOError: # [Errno13] Permission denied: 
				cfg_file = default_conf_files[0]
	if not os.path.isfile(cfg_file):
		if new:
			import logging
			msgs.append((logging.INFO, "creating new configuration file '%s'", cfg_file))
			cfg_dir = os.path.dirname(cfg_file)
			if not os.path.isdir(cfg_dir):
				os.makedirs(cfg_dir)
			with open(cfg_file, 'w'):
				pass # touch
		else:
			raise IOError(err_msg_if_missing)
	with open(cfg_file, 'r') as f:
		while True:
			line = f.readline()
			if f.tell() == 0: # file is empty
				break
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
		assert isinstance(raw_cfg, str)
		config = ConfigParser()
		import io
		try:
			config.readfp(io.BytesIO(raw_cfg), filename=cfg_file)
		except UnicodeDecodeError:
			raw_cfg = "\n".join([ line.decode('utf-8').encode('unicode-escape')
					for line in raw_cfg.splitlines() ])
			config.readfp(io.BytesIO(raw_cfg), filename=cfg_file)
			config = crawl_config(lambda a: a.decode('unicode-escape'), config)
	config.filename = cfg_file
	return (config, cfg_file, msgs)


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
	* ``protocol://servername[:port][/relativepath]

	Note that ``absolutepath`` must start with *'/'* or *'~/'* to be identified
	as an absolute path.

	``absolutepath`` and ``servername`` are returned as second argument and 
	``relativepath`` as fourth output argument.

	*new in 0.5:* `multi_path_protocols`

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


def crawl_config(fun, config=None):
	def crawl(__config__):
		__defaults__ = __config__.defaults()
		for __option__, __value__ in __defaults__.items():
			__config__.set(default_section, __option__, fun(__value__))
		for __section__ in __config__.sections():
			for __option__, __value__ in __config__.items(__section__):
				__config__.set(__section__, __option__, fun(__value__))
		return __config__
	if config:
		return crawl(config)
	else:
		return crawl


def get_dist_file(default_dirs={}, filename=None,
		config=None, section=None, option=None):
	if config is None:
		config, cfg_file, _ = parse_cfg()
	elif isinstance(config, ConfigParser):
		cfg_file = config.filename
	else:
		cfg_file = config
		config = None
	undefined = True
	dist_dir, cfg_basename = os.path.split(cfg_file)
	if option and config is not None:
		if section is None:
			section = default_section
		try:
			dist_dir = getpath(config, section, option)
		except NoOptionError:
			pass
		else:
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
	pid_file = get_dist_file(default_run_dirs, config=config)
	if not pid_file.endswith('.pid'):
		pid_file += '.pid'
	return pid_file


def get_cache_file(config=None, section=None, prefix='', previously=None):
	"""
	Get the corresponding persistent data location for a given configuration 
	file and section.

	Arguments:

		* config (ConfigParser): configuration object.

		* section (str): section/repository name.

		* prefix (str): prefixes the basename of the returned path.

		* previously (str): former section/repository name if it has been renamed.

	Returns:

		str: path to persistent data location.
	"""
	cache_option = 'cache'
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
			option=cache_option)
	if not config.has_option(section, cache_option) or \
			(config.has_option(default_section, cache_option) and \
				config.get(section, cache_option) == config.get(default_section, cache_option)):
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


def write_config(cfg_file, config):
	# moved from cli.config.config
	import codecs
	with codecs.open(cfg_file, 'w', encoding='utf-8') as f:
		config.write(f)
	# remove the default section header
	with open(cfg_file, 'r') as f:
		raw_cfg = f.readlines()
	default_header = '[{}]'.format(default_section)
	for i, line in enumerate(raw_cfg):
		header_found = line.startswith(default_header)
		if header_found:
			break
	if header_found:
		raw_cfg = raw_cfg[:i] + raw_cfg[i+1:]
		with open(cfg_file, 'w') as f:
			for line in raw_cfg:
				f.write(line)

