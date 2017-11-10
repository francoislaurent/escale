# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent
#   Contributions:
#     * `ssl_version`, `verify_ssl`, `filetype`, `quota` in `fields`
#     * `_item_separator`, `getlist`, `getunit`, `storage_space_unit` (dict() statement)
#     * `list = getlist` and `number_unit = getnum` lines in `getter`
#     * `checksum` in `fields`
#     * `includedirectory` and `excludedirectory` in `fields`
#     * `checksumcache` in `fields`

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
# 'locktimeout', 'mode' and 'count' added in version 0.5-?
# 'pattern' becomes 'include' in version 0.5rc2
# 'exclude' added in version 0.5rc2
# 'checksum' added in version 0.5.1
# 'minsplitsize' added in version 0.6rc2
# 'maxpendingtransfers' added in version 0.6rc2
# 'compact' added in version 0.7alpha, renamed 'index' in 0.7rc1
# 'maxpagesize' added in version 0.7rc1
# 'includedirectory' and 'excludedirectory' added in version 0.7.1
# 'checksumcache' added in version 0.7.1
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
	include=('list', ['include', 'include files', 'pattern', 'filter']),
	exclude=('list', ['exclude', 'exclude files']),
	quota=('number_unit', ['disk quota', 'quota']),
	maintainer=['maintainer', 'email'],
	certfile=('path', ['certfile', 'cert file', 'certificate']),
	keyfile=('path', ['keyfile', 'key file', 'private key']),
	locktimeout=(('bool', 'int'), ['lock timeout']),
	mode=['mode', 'synchronization mode'],
	count=('int', ['puller count', 'pullers']),
	checksum=(('bool', 'str'), ['checksum', 'hash algorithm']),
	minsplitsize=('int', ['min split size', 'split size', 'split']),
	maxpendingtransfers=('int', ['max pending transfers']),
	index=(('bool', 'str'), ['index', 'compact']),
	maxpagesize=('number_unit', ['maxpagesize', 'maxarchivesize']),
	includedirectory=('list', ['include directory', 'include directories']),
	excludedirectory=('list', ['exclude directory', 'exclude directories']),
	checksumcache=(('bool', 'path'), ['checksum cache']))


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
	return parse_num(value)

def parse_num(value):
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
	if not isinstance(attrs, (tuple, list)):
		attrs = [attrs]
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


def actual_option(config, section, options):
	# largely borrowed from :func:`escale.cli.config.config.query_field`
	option = None
	if isinstance(options, tuple):
		_type, options = options
		if isinstance(_type, tuple):
			_type = _type[0] # not used
	if isinstance(options, list):
		for _option in options:
			if config.has_option(section, _option):
				option = _option
				break
	elif config.has_option(section, options):
		option = options
	return option


def full_address(config, section):
	protocol = parse_field(config, section, 'protocol')
	if not protocol:
		raise ValueError("'protocol' not defined")
	path = parse_field(config, section, fields['directory'])
	if protocol == 'file':
		if not path:
			raise ValueError("'relay path' not defined")
		return path
	else:
		address = parse_field(config, section, fields['address'])
		if address:
			address += '/'
		else:
			address = ''
		if path is None:
			path = ''
		return ''.join([
				protocol,
				'://',
				address,
				path,
				])

