# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.config import *
import escale.relay as relay
import escale.encryption as encryption
import socket

try:
	from configparser import NoOptionError # Py3
except ImportError:
	from ConfigParser import NoOptionError # Py2


def get_client_name(repository, config={}):
	try:
		return config.pop('clientname')
	except KeyError:
		try:
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
		if cipher is None:
			del args['encryption']
		else:
			args['encryption'] = cipher(args['passphrase'])
	relay_class = relay.by_protocol(args['protocol'])
	return (relay_class, args)

