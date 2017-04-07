
try:
	from configparser import ConfigParser, NoOptionError
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser
	NoOptionError = cp.NoOptionError
import argparse
import sys
import os

import syncacre.relay as relay
from syncacre.manager import Manager
import syncacre.encryption as encryption

from functools import partial
from multiprocessing import Pool


PYTHON_VERSION = sys.version_info[0]

default_section = 'DEFAULT' # Python2 cannot modify it


# fields expected in configuration files
fields = dict(path=['local path', 'path'], \
	address=['relay address', 'remote address', 'address'], \
	directory=['relay dir', 'remote dir', 'dir', 'relay directory', 'remote directory', 'directory'], \
	port=['relay port', 'remote port', 'port'], \
	username=['relay user', 'remote user', 'auth user', 'user'], \
	password=['password', 'secret', 'secret file', 'secrets file', 'credential', 'credentials'], \
	refresh=('float', ['refresh']), \
	timestamp=('bool', ['modification time', 'timestamp', 'mtime']), \
	clientname=['client', 'client name'], \
	encryption=['encryption'], \
	passphrase=['passphrase', 'key'])


def getters(config, _type=None):
	if _type:
		return dict(bool=config.getboolean, int=config.getint, float=config.getfloat)[_type]
	else:
		return config.get


def syncacre(config, repository):
	"""
	Reads the section related to a repository in a loaded configuration object and spawns a 
	:class:`~syncacre.manager.Manager` for that repository.
	"""
	args = {}
	for field, attrs in fields.items():
		if isinstance(attrs, tuple):
			t, attrs = attrs
			get = getters(config, t)
		else:
			get = getters(config)
		for attr in attrs:
			try:
				args[field] = get(repository, attr)
				break
			except NoOptionError:
				pass
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
					if verbose:
						print('cannot read password for user {} from file {}'.format(args['username'], args[ 'password']))
					del args['password']
		else:
			try:
				args['username'], args['password'] = content[0].split(':', 1)
			except ValueError:
				if verbose:
					print('cannot read login information from credential file {}'.format(args['password']))
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
				if verbose:
					print('both read only and write only; cannot determine mode')
				return
			else:
				args['mode'] = 'upload'
	except NoOptionError:
		pass
	# parse encryption passphrase
	if 'passphrase' in args and os.path.isfile(args['passphrase']):
		with open(args['passphrase'], 'r') as f:
			args['passphrase'] = f.read()
	if 'encryption' in args:
		try:
			cipher = encryption.by_cipher(args['encryption'].lower())
		except KeyError:
			raise ValueError('unsupported encryption algorithm: {}'.format(args['encryption']))
		args['encryption'] = cipher(args.pop('passphrase', None))
	try:
		protocol = config.get(repository, 'protocol')
	except NoOptionError:
		protocol = args['address'].split(':')[0] # crashes if no colon found
	if PYTHON_VERSION == 3:
		args['config'] = config[repository]
	elif PYTHON_VERSION == 2:
		args['config'] = (config, repository)
	manager = Manager(relay.by_protocol(protocol), protocol=protocol, **args)
	manager.run()


def uncurried_syncacre(args):
	"""
	Python2 adapter for :meth:`multiprocessing.pool.Pool.map`.
	"""
	syncacre(*args)


def main(**args):
	"""
	Parses a configuration file and calls `syncacre` on each declared repository.
	"""
	verbose = not args['quiet']

	cfg_file = args['config']
	if cfg_file:
		if not os.path.isfile(cfg_file):
			if verbose:
				print('file not found: {}'.format(cfg_file))
			cfg_file = None
	else:
		candidates = [os.path.expanduser('~/.config/syncacre.conf'), \
			os.path.expanduser('~/.syncacre'), \
			'/etc/syncacre.conf', \
			None]
		for cfg_file in candidates:
			if cfg_file and os.path.isfile(cfg_file):
				break
	if cfg_file:
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
		if not args['quiet']:
			config.set(default_section, 'verbose', '0')
		if args['daemon']:
			config.set(default_section, 'daemon', '1')
		nsections = len(config.sections())
		if nsections == 1:
			syncacre(config, config.sections()[0])
		else:
			pool = Pool(nsections)
			if PYTHON_VERSION == 3:
				pool.map(partial(syncacre, config), config.sections())
			elif PYTHON_VERSION == 2:
				import itertools
				pool.map(uncurried_syncacre, \
					itertools.izip(itertools.repeat(config), config.sections()))
		out = 0
	else:
		if verbose:
			out = 'cannot find a valid configuration file'
		else:
			out = 0
	return out




if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog='syncacre', \
		description='ACRosS - All-Clients Relay Synchronizer', \
		epilog='See also https://github.com/francoislaurent/syncacre')
	parser.add_argument('-c', '--config', type=str, help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon (recommended)')
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently')

	args = parser.parse_args()
	exit_code = main(**args.__dict__)
	sys.exit(exit_code)

