# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.config import *
from escale.relay import __multi_path_protocols__
import os
import stat
import codecs
import logging
from getpass import *
import base64
import importlib

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass

tab = "\t"

multi_path_protocols = __multi_path_protocols__
path_only_protocols = [ 'file' ] + multi_path_protocols
standard_protocols = [ 'ftp', 'ftps', 'http', 'https', 'webdav' ]

def show_protocols(ps):
	p = ["'{}'"]
	for _ in ps[1:-1]:
		p.append(", '{}'")
	if p[1:]:
		p.append(" or '{}'")
	return ''.join(p).format(*ps)


def query_field(config, section, field, description=None, suggestion='', required=False, echo=True):
	'''
	Request user input for a single field.

	If `field` is in `~escale.base.config.fields`, `query_field` will seek in `config` for any of 
	the candidate options defined in `fields`, instead of `field`.

	If an existing value is found, it is presented as a default value and returned as answer if
	the user does not input anything.

	Arguments:

		config (ConfigParser): existing configuration.

		section (str): active configuration section.

		field (str): any key from `~escale.base.config.fields` or any configuration option.

		description (str): request text.

		suggestion (str): an indication of default value or possible choices.

		required (bool): if True, the request is drawn again as long as the user do not input 
			a non-empty answer.

		echo (bool): if False, the answer is not echoed (suitable for passwords).

	Returns:

		(str, str): first argument is the actual option name in `config`. 
		Second argument is the user's answer.
	'''
	option = None
	if field in fields:
		_fields = fields[field]
		if isinstance(_fields, tuple):
			_type, _fields = _fields
			if isinstance(_type, tuple):
				_type = _type[0] # not used
		assert isinstance(_fields, list)
		for field in _fields:
			if config.has_option(section, field):
				option = field
				break
		field = _fields[0]
	if not option:
		option = field
	if not description:
		description = field
	existing = config.has_option(section, option)
	if existing:
		existing = config.get(section, option) # existing value presented as default one
		#if not suggestion:
		suggestion = existing # existing value should be favored
	if echo:
		_input = input
	else:
		_input = getpass
	if not suggestion and required:
		answer = None
		while not answer:
			answer = _input('{} (required): '.format(description))
	else:
		answer = _input('{}: [{}] '.format(description, suggestion))
		if not answer and existing:
				answer = existing
		# an empty answer represents `suggestion`, do not return `suggestion`
	return (option, answer)


def add_section(cfg_file, msgs=[]):
	'''
	Add or edit a section of a configuration file.

	Arguments:

		cfg_file (str): path to a configuration file.

		msgs (list): pending messages.

	Returns:

		list: pending messages.
	'''
	print(__package__)
	# note: enjoy reading this nice white elephant code
	config, cfg_file, msgs = parse_cfg(cfg_file, msgs, True)
	cfg_dir = os.path.dirname(cfg_file)
	if cfg_dir == global_cfg_dir: # superuser mode
		#cfg_dir = os.path.join(global_cfg_dir, PROGRAM_NAME) # /etc/escale
		#if not os.path.isdir(cfg_dir):
		#	if os.path.exists(cfg_dir):
		#		raise RuntimeError("'{}' should be a directory".format(cfg_dir))
		#		os.unlink(cfg_dir)
		#	os.mkdir(cfg_dir)
		_log_file_ = 'log file'
		try:
			log_file = config.get(default_section, _log_file_)
		except:
			log_file = None
		else:
			if not os.path.isabs(log_file) or log_file.startswith(global_cfg_dir):
				msg = "logging in '{}' is not permitted; fixing '{}'".format(global_cfg_dir, _log_file_)
				msgs.append((logging.DEBUG, msg))
				print(msg)
				log_file = None
		if not log_file:
			log_file = '/var/log/{}.log'.format(PROGRAM_NAME)
			config.set(default_section, _log_file_, log_file)
	msg = "editing configuration file '{}'".format(cfg_file)
	msgs.append((logging.DEBUG, msg))
	print(msg)
	if not os.path.isabs(cfg_dir):
		cfg_dir = os.path.join(os.getcwd(), cfg_dir)
	while True:
		sections = config.sections()
		if sections:
			print("existing section(s):")
			for section in sections:
				print("{}. '{}'".format(tab, section))
		print('please prefer ascii names')
		section = input('section name (required): ')
		new = section not in sections
		if new:
			config.add_section(section)
		## local repository (unicode is alright)
		_rep_, rep = query_field(config, section, 'path', required=True)
		if rep and rep[0] == '~':
			rep = os.path.expanduser(rep)
		if not os.path.isabs(rep):
			rep = os.path.join(os.getcwd(), rep)
		if not os.path.isdir(rep):
			msg = "making directory '{}'".format(rep)
			msgs.append((logging.DEBUG, msg))
			print(msg)
			os.makedirs(rep)
		config.set(section, _rep_, rep)
		## host address
		if new:
			protocol = None
		else:
			# check whether section is well formatted
			protocol = parse_field(config, section, default_option('protocol', all_options=True))
		if not protocol:
			print("")
			print("a host address should be in the form:")
			print("  file:///path")
			print("")
			print("or:")
			print("  googledrive[://path]")
			print("  googledrive:///mountpoint[//path]")
			print("where '/mountpoint' is the absolute path to a local mount")
			print("and 'path' is the path of the relay directory relative to")
			print("the mount point")
			print("")
			print("or:")
			print("  protocol://servername[:port][/path]")
			print("if 'protocol' is any of:")
			print(show_protocols(standard_protocols))
			print("")
			_addr_, addr = query_field(config, section, 'address', required=True)
			protocol, servername, port, path = parse_address(addr,
					multi_path_protocols=multi_path_protocols)
			if protocol:
				config.set(section, default_option('protocol'), protocol)
			if servername:
				config.set(section, _addr_, servername)
			if port:
				config.set(section, default_option('port'), port)
			if path:
				config.set(section, default_option('directory'), path)
		else:
			# first, determine whether host is 
			#   protocol:///path
			# or
			#   protocol://servername[:port][/path]
			if protocol in multi_path_protocols:
				_, addr = query_field(config, section, 'address',
						description='mount point or address')
				if addr:
					config.set(section, 'relay address', addr)
				_path_ = 'remote directory'
				_, path = query_field(config, section, 'directory',
						description=_path_)
				if path:
					config.set(section, _path_, path)
			elif protocol in path_only_protocols:
				_, path = query_field(config, section, 'directory',
						description='mount point')
				if path:
					config.set(section, 'relay directory', path)
				# ensure that 'address' and 'port' are not defined
				for undesirable_option in fields['port']+fields['address']:
					try:
						config.remove_option(section, undesirable_option)
					except:
						pass
			else:
				_addr_, servername = query_field(config, section, 'address', description='server name',
						required=True)
				if servername:
					config.set(section, _addr_, servername)
				# offer to modify protocol for cases such as 'ftp' <-> 'ftps', 'http' <-> 'https'
				_proto_, protocol = query_field(config, section, 'protocol')
				if protocol:
					if protocol in path_only_protocols: # this will prevent only a few misuses
						raise ValueError('cannot switch from a family of protocols to another; use `escalectl migrate` instead')
					config.set(section, _proto_, protocol)
				if parse_field(config, section, fields['port']):
					_port_, port = query_field(config, section, 'port')
					if port:
						config.set(section, 'port', port)
				_, host_path = query_field(config, section, 'directory')
				if host_path:
					config.set(section, 'host path', host_path) # host path introduced in 0.4a3
		## client name
		print('the client name should uniquely identify the client among all the nodes')
		print(' that operate on the same relay repository')
		print(' (please prefer ascii names)')
		_client_, client = query_field(config, section, 'clientname', suggestion=section)
		if client:
			config.set(section, _client_, client)
		if protocol != 'file':
			## secret
			# username
			secret_file = None
			print('if the credentials are available in a file, leave the following field empty')
			_username_, username = query_field(config, section, 'username',
				description='authentification username')
			if username:
				# password
				_, password = query_field(config, section, 'password', echo=False)
				if password:
					if os.path.isfile(password):
						print("'{}' exists as a file".format(password))
						print("if credentials are to be found in a file, they should be provided as 'username:password'")
						raise ValueError('wrong password')
					ext = '.credential'
					if client:
						basename = client
					else:
						credentials = [ f[:-len(ext)] for f in os.listdir(cfg_dir)
							if f.endswith(ext) ]
						if credentials:
							basename = 0
							while str(basename) in credentials:
								basename += 1
							basename = str(basename)
						else:
							basename = '0'
					secret_file = os.path.join(cfg_dir, basename + ext)
					msg = "writing new credential file '{}'".format(secret_file)
					if os.path.isfile(secret_file):
						msg = 'over' + msg
					msgs.append((logging.DEBUG, msg))
					print(msg)
					if PYTHON_VERSION == 2: # handle unicode
						if isinstance(username, unicode):
							username = username.encode('utf-8')
						if isinstance(password, unicode):
							password = password.encode('utf-8')
					credential = '{}:{}'.format(username, password)
					with open(secret_file, 'w') as f:
						f.write(credential)
					try:
						os.chmod(secret_file, stat.S_IRUSR | stat.S_IWUSR)
					except OSError as e:
						msg = 'could not change permissions on credential file'
						msgs.append((logging.DEBUG, e))
						msgs.append((logging.DEBUG, msg))
						print(e)
						print(msg)
					config.set(section, 'secret file', secret_file)
				else:
					config.set(section, _username_, username)
			else:
				# secret file
				_secret_ = 'secret file'
				_, secret_file = query_field(config, section, 'password',
						description=_secret_)
				if secret_file:
					if not os.path.isabs(secret_file):
						if os.path.isfile(secret_file):
							secret_file = os.path.join(os.getcwd(), secret_file)
						else:
							secret_file = os.path.join(cfg_dir, secret_file)
					if not os.path.isfile(secret_file):
						msg = "'{}' file does not exist yet; create it before running {}".format(secret_file, PROGRAM_NAME)
						msgs.append((logging.DEBUG, msg))
						print(msg)
					config.set(section, _secret_, secret_file)
		## encryption
		_enc_, encryption = query_field(config, section, 'encryption', suggestion='on')
		if encryption:
			encryption = encryption.lower()
		else:
			encryption = 'on'
		config.set(section, _enc_, encryption)
		# encryption passphrase
		if encryption not in [ '0', 'off', 'no', 'false' ]:
			_pass_, passphrase = query_field(config, section, 'passphrase', required=True)
			if not os.path.isabs(passphrase):
				if os.path.isfile(passphrase):
					passphrase = os.path.join(os.getcwd(), passphrase)
				else:
					passphrase = os.path.join(cfg_dir, passphrase)
			if not os.path.isfile(passphrase):
				print("'{}' file does not exist yet".format(passphrase))
				gen = input('generate a new key? [Y/n] ').lower()
				if not gen or gen[0] == 'y':
					key = base64.urlsafe_b64encode(os.urandom(32))
					print('{}key: {}'.format(tab, key))
					msg = "writing new passphrase file '{}'".format(passphrase)
					msgs.append((logging.DEBUG, msg))
					with open(passphrase, 'w') as f:
						f.write(key)
					try:
						os.chmod(passphrase, stat.S_IRUSR | stat.S_IWUSR)
					except OSError as e:
						msg = 'could not change permissions on passphrase file'
						msgs.append((logging.DEBUG, e))
						msgs.append((logging.DEBUG, msg))
						print(e)
						print(msg)
				else:
					msg = "create '{}' file before running {}".format(passphrase, PROGRAM_NAME)
					msgs.append((logging.DEBUG, msg))
					print(msg)
			config.set(section, _pass_, passphrase)
		## synchronization mode
		# get existing value, if any
		# and delete all the options found to handle all kind of conflicts
		mode = ''
		pull_only = False
		for option in fields['pull_only'][1][::-1]:
			try:
				pull_only = config.getboolean(section, option)
			except:
				pass
			else:
				pull_option = option
				config.remove_option(section, option)
		if pull_only:
			mode = 'download'
		#else:
		# handle broken configuration files that set both `pull only` and `push only`
		# or also `read only` and `write only`
		push_only = False
		for option in fields['push_only'][1][::-1]:
			try:
				push_only = config.getboolean(section, option)
			except:
				pass
			else:
				push_option = option
				config.remove_option(section, option)
		if push_only:
			if pull_only: # broken configuration file
				msg = "both `push only` and `pull only` defined; discarding both settings"
				msgs.append((logging.DEBUG, msg))
				print(msg)
				mode = ''
			else:
				mode = 'upload'
		# ask for mode
		if mode:
			suggestion = mode
		else:
			suggestion = 'shared'
		print("")
		print("synchronization mode can be 'upload', 'download', 'shared' or 'conservative'")
		if not mode: # explain roughly
			print(tab + ". 'upload': your local files will be sent to the relay repository")
			print(tab + "            your local files will not be modified")
			print(tab + ". 'download': you will get files from the relay repository")
			print(tab + "              your local files will not be sent over the internet")
			print(tab + "              but they can be modified")
			print(tab + ". 'shared': your files will be fully synchronized")
			print(tab + ". 'conservative': your local files will be sent to the relay repository")
			print(tab + "                  but will not be modified")
			print(tab + "                  you will get only new files from the relay repository")
			print("")
		_mode_, answer = query_field(config, section, 'mode',
				description="which mode for this client?", suggestion=suggestion)
		# write down (no need to do so with 'shared')
		if answer:
			config.set(section, _mode_, answer)
		elif mode: # `pull only` or `push only` were defined
			# let the original option (almost) untouched
			if pull_only:
				config.set(section, pull_option, 'yes')
			elif push_only:
				config.set(section, push_option, 'yes')
		## refresh rate (let's make it explicit/visible in the configuration file)
		default_refresh = '10'
		_refresh_, refresh = query_field(config, section, 'refresh',
			description='refresh interval (in seconds)', suggestion=default_refresh)
		if not refresh:
			refresh = default_refresh
		config.set(section, _refresh_, refresh)
		# disk quota for webdav
		if mode != 'download':
			print("quotas on the amount of sent data are recommended for pushers")
			print(" examples:  2GB  4.5G  1To  (default unit is gigabyte)")
			_quota_, quota = query_field(config, section, 'quota')
			if quota:
				config.set(section, _quota_, quota)
		# delegate protocol dependent setup
		try:
			extra_mod = importlib.import_module('.'.join((__package__, protocol)))
		except ImportError:
			pass
		else:
			try:
				result = extra_mod.setup(config, section)
			except Exception as e:
				import traceback
				print(traceback.format_exc())
				print(e)
				print('aborted.')
			else:
				if type(result) is type(config):
					config = result
		## stop
		if not input('do you want to add/edit another section? [N/y] ').lower().startswith('y'):
			break
	# write configuration
	write_config(cfg_file, config)
	return msgs

