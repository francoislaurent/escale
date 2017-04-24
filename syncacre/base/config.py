# -*- coding: utf-8 -*-

from .essential import *
import os
try:
	from configparser import ConfigParser, NoOptionError
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser
	NoOptionError = cp.NoOptionError



# configparser
default_section = 'DEFAULT' # Python2 cannot modify it

default_conf_files = [os.path.expanduser('~/.config/syncacre/syncacre.conf'),
	os.path.expanduser('~/.syncacre/syncacre.conf'),
	'/etc/syncacre.conf']


# fields expected in configuration files
fields = dict(path=('path', ['local path', 'path']),
	address=['relay address', 'remote address', 'host address', 'address'],
	directory=['relay dir', 'remote dir', 'host dir', 'dir', 'relay directory', 'remote directory',
		'host directory', 'directory'],
	port=['relay port', 'remote port', 'host port', 'port'],
	username=['relay user', 'remote user', 'host user', 'auth user', 'user'],
	password=(('path', 'str'),
		['password', 'secret', 'secret file', 'secrets file', 'credential', 'credentials']),
	refresh=('float', ['refresh']),
	timestamp=(('bool', 'str'), ['modification time', 'timestamp', 'mtime']),
	clientname=['client', 'client name'],
	encryption=(('bool', 'str'), ['encryption']),
	passphrase=(('path', 'str'), ['passphrase', 'key']),
	push_only=('bool', ['read only', 'push only']),
	pull_only=('bool', ['write only', 'pull only']),
	ssl_version=['ssl version'],
	verify_ssl=('bool', ['verify ssl']),
	file_type=('list', ['file extension', 'file type']))


def getpath(config, section, attr):
	path = config.get(section, attr)
	if path[0] == '~':
		path = os.path.expanduser(path)
	if os.path.isdir(os.path.dirname(path)):
		return path
	else:
		raise ValueError


_item_separator = ','

def getlist(config, section, attr):
	_list = [ i.strip() for i in config.get(section, attr).split(_item_separator) ]
	return [ i for i in _list if i ]



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
			list =	getlist
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


def parse_cfg(cfg_file, msgs):
	if cfg_file:
		if not os.path.isfile(cfg_file):
			raise IOError('file not found: {}'.format(cfg_file))
	else:
		candidates = default_conf_files + [None]
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
	return (config, cfg_file, msgs)

