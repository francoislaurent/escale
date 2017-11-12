# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2017, Institut Pasteur
#    Contributor: François Laurent
#    Contribution: query_local_repository, query_relay_address,
#                  add_section rewrite, edit_section, edit_config,
#                  section_common, simplified_add

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from ..format import *
from escale.base.essential import copyfile, quote_join
from escale.base.exceptions import *
from escale.base.config import *
from escale.relay import __multi_path_protocols__
from escale.manager.config import *
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
help_cmd = '?'
help_instructions = "request help with '{}'".format(help_cmd)

multi_path_protocols = __multi_path_protocols__
oauth_protocols = __multi_path_protocols__ # may no longer be true in the future
path_only_protocols = [ 'file' ] + multi_path_protocols
standard_protocols = [ 'ftp', 'ftps', 'http', 'https', 'webdav' ]

def show_protocols(ps):
	return quote_join(ps)

def _indexing(protocol):
	return protocol not in [ 'ftp', 'ftps', 'file' ]


def print_help(help, space=True):
	if help:
		if isinstance(help, (list, tuple)):
			if space:
				print('')
			for _help in help:
				if isinstance(_help, (list, tuple)):
					multiline_print(*_help)
				else:
					multiline_print(_help)
				if space:
					print('')
		else:
			multiline_print(help)


def query_field(config, section, field, description=None, suggestion='', required=False, echo=True,
		help=None, reminder=True):
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

		help (str): help message displayed when the user inputs '?'.

		reminder (bool): if True, a reminder about help availability is printed.

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
	if help and reminder:
		multiline_print(help_instructions)
	if echo:
		_input = input
	else:
		_input = getpass
	if not suggestion and required:
		while True:
			answer = _input(decorate_line('{} (required): '.format(description)))
			if answer == help_cmd:
				print_help(help)
			elif answer:
				break
	else:
		if suggestion is None:
			suggestion = ''
		if description[-1] in '.:!?,;=':
			colon = ''
		else:
			colon = ':'
		while True:
			answer = _input(decorate_line('{}{} [{}] '.format(description, colon, suggestion)))
			if answer == help_cmd:
				print_help(help)
			else:
				break
		if not answer and existing:
				answer = existing
		# an empty answer represents `suggestion`, do not return `suggestion`
	return (option, answer)


def query_local_repository(config, section=None, msgs=[]):
	'''
	Query local repository.

	Unicode is alright.

	Returns:

		(str, str): configuration option and value.
	'''
	description = 'path of your local repository'
	if section:
		_rep_, rep = query_field(config, section, 'path', description, required=True)
	else:
		_rep_ = default_option('path')
		rep = None
		while not rep or rep == help_cmd:
			rep = input(decorate_line('{} (required): '.format(description)))
	if rep and rep[0] == '~':
		rep = os.path.expanduser(rep)
	if not os.path.isabs(rep):
		rep = os.path.join(os.getcwd(), rep)
	if not os.path.isdir(rep):
		msg = "making directory '{}'".format(rep)
		msgs.append((logging.DEBUG, msg))
		debug_print(msg)
		os.makedirs(rep)
	return (_rep_, rep, msgs)


def query_relay_address(config, section=None, remote=True, msgs=[], help=None):
	if remote:
		description = 'address of the relay repository'
	else:
		description = 'path of the locally accessible relay repository'
	if help is None:
		if remote:
			help = [[
				"enter the relay host address",
				],[
				"a host address should be in the form:",
				"  protocol://servername[:port][/path]",
				"if 'protocol' is any of:",
				"  "+show_protocols(standard_protocols),
				],[
				"some protocols do not even need a server name, e.g.:",
				"  googledrive[://path]",
				]]
		else:
			help = [[
				"enter the path of locally accessible directory",
				],[
				"if you intend to use Google Drive mounted with",
				"the drive utility, you can alternatively specify:",
				"  googledrive:///mountpoint[//path]",
				"where '/mountpoint' is the absolute path to a local",
				"mount and 'path' is the path of the relay directory",
				"relative to the mount point",
				]]
	if section:
		_addr_, addr = query_field(config, section, 'address',
			description=description, required=True, help=help)
	else:
		_addr_ = default_option('address')
		while True:
			addr = input(decorate_line(description+' (required): '))
			if addr == help_cmd:
				print_help(help)
			elif addr:
				break
	protocol, servername, port, path = parse_address(addr,
			multi_path_protocols=multi_path_protocols)
	if section:
		section_exists = config.has_section(section)
		if protocol:
			required_or_default = False
		elif remote:
			required_or_default = True
		else:
			# enforce 'file' as a protocol if not any; if the user wanted 
			# another protocol (e.g. 'googledrive') she should have specified 
			# it in the relay repository address
			required_or_default = False#'file'
		# check existing fields and request new values for the existing fields
		_fields_ = {
			'protocol':	('protocol', protocol, required_or_default),
			'port':		('port', port, False),
			'path to relay repository':	('directory', path, False),
			}
		for key in _fields_:
			field, new_value, required = _fields_[key]
			if section_exists:
				try:
					options = fields[field]
				except KeyError:
					options = field
				option = actual_option(config, section, options)
			else:
				option = None
			if option:
				# old_value does exist
				old_value = config.get(section, option)
				if new_value:
					if old_value != new_value:
						msg = "{} '{}' modified to: '{}'".format(key, old_value, new_value)
						msgs.append((logging.INFO, msg))
						multiline_print(msg)
				else:
					new_value = old_value
			else:
				option = default_option(field)
				if not new_value:
					if required is True:
						while not new_value or new_value == help_cmd:
							new_value = input(decorate_line(key+' (required): '))
					elif required:
						# `required` contains default value
						suggestion = required
						new_value = help_cmd
						while new_value == help_cmd:
							new_value = input(decorate_line(
								'{}: [{}] '.format(key, suggestion)))
						if not new_value:
							new_value = suggestion
			_fields_[key] = (option, new_value)
		_prot_, protocol = _fields_['protocol']
		_port_, port = _fields_['port']
		_path_, path = _fields_['path to relay repository']
		# TODO: clean-up `config`, especially if `protocol` has been modified
	else:
		_prot_ = default_option('protocol')
		_port_ = default_option('port')
		_path_ = default_option('directory')
	if not protocol and not remote:
		protocol = 'file'
	addr_dict = {_prot_: protocol, _addr_: servername, _port_: port, _path_: path}
	if section:
		if not config.has_section(section):
			config.add_section(section)
		for option, value in addr_dict.items():
			if value:
				config.set(section, option, value)
	return (config, addr_dict, msgs)


def edit_config(cfg_file, msgs=[]):
	'''
	Add or edit sections of a configuration file.

	Arguments:

		cfg_file (str): path to a configuration file.

		msgs (list): pending messages.

	Returns:

		list: pending messages.
	'''
	# code moved from `add_section`
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
				debug_print(msg)
				log_file = None
		if not log_file:
			log_file = '/var/log/{}.log'.format(PROGRAM_NAME)
			config.set(default_section, _log_file_, log_file)
	msg = "editing configuration file '{}'".format(cfg_file)
	msgs.append((logging.DEBUG, msg))
	debug_print(msg)
	if not os.path.isabs(cfg_dir):
		cfg_dir = os.path.join(os.getcwd(), cfg_dir)
	while True:
		sections = config.sections()
		section = None
		if sections:
			if sections[1:]:
				plural = 's'
			else:
				plural = ''
			help = [["existing section{}:".format(plural)],
				[ "{}. '{}'".format(tab, _section) for _section in sections ],
				['prefer ascii names']]
			print_help(help, space=False)
			while not section:
				section = input(decorate_line('section name (required): '))
				if section == help_cmd:
					print_help(help, space=False)
					section = None
		mode = input(decorate_line("run in simplified mode: [Y/n] "))
		if mode and mode[0].lower() == 'n':
			if section in sections:
				config, msgs = edit_section(config, cfg_dir, section, msgs)
			else:
				config, msgs = add_section(config, cfg_dir, section, msgs)
		else:
			config, msgs = simplified_add(config, cfg_dir, section, msgs)
			break
		## stop
		if not input(decorate_line('do you want to add/edit another section? [N/y] ')).lower().startswith('y'):
			break
	# write configuration
	write_config(cfg_file, config)
	return msgs


def add_section(config, cfg_dir, section=None, msgs=[]):
	'''
	Add a configuration section.

	Asks for information in the following order:

	* local repository (path)
	* remote address or locally accessible relay repository (mount)?
		* locally accessible relay repository (path)
		* or relay full address (protocol://address:port/path)
	* section name if missing
	
	And then delegates to :func:`section_common`.

	*new in 0.7:* indexing is set by default, with 200MB page size, for all relay backend but *FTP* and *local file*.

	Arguments:

		config (ConfigParser): configuration object.

		cfg_dir (str): configuration directory.

		section (str): configuration section name.

		msgs (list): pending messages.

	Returns:

		(ConfigParser, list): updated configuration object and pending messages.
	'''
	_rep_, rep, msgs = query_local_repository(config, section, msgs)
	## host address
	answer = input(decorate_line("is the relay repository locally mounted in the file system? [N/y] "))
	remote = not answer or answer[0].lower() == 'n'
	config, kwargs, msgs = query_relay_address(config, section, remote, msgs)
	help = [
		'choose a name for this configuration section',
		'prefer ascii names',
		]
	while not section:
		section = input(decorate_line('section name (required): '))
		if section == help_cmd:
			print_help(help)
			section = None
	msgs.append((logging.DEBUG, "editing the '%s' configuration section", section))
	if not config.has_section(section):
		config.add_section(section)
	config.set(section, _rep_, rep)
	for option, value in kwargs.items():
		if value:
			config.set(section, option, value)
	protocol = kwargs['protocol']
	config, mode, msgs = section_common(config, cfg_dir, section, protocol, msgs,
		return_mode=True)
	if _indexing(protocol):
		# new in 0.7: indexing is default behaviour
		config.set(section, default_option('index'), '1')
		if mode != 'download':
			config.set(section, default_option('maxpagesize'), '200MB')
	# new in 0.7.1: checksum caching is default behaviour
	config.set(section, default_option('checksumcache'), 'on')
	return config, msgs


def section_common(config, cfg_dir, section, protocol, msgs, return_mode=False):
	# code moved from `add_section`
	## client name
	help = [
		'choose a client name',
		[
		'the client name should uniquely identify the client among all the nodes',
		'that operate on the same relay repository',
		],
		'prefer ascii name',
		]
	suggestion = get_client_name(section)
	_client_, client = query_field(config, section, 'clientname', suggestion=suggestion, help=help)
	if not client:
		client = suggestion
	config.set(section, _client_, client)
	if protocol not in ['file']+oauth_protocols:
		## secret
		# username
		secret_file = None
		multiline_print(
			'if the credentials are available in a file, leave the following field empty')
		_username_, username = query_field(config, section, 'username',
			description='authentification username')
		if username:
			# password
			_, password = query_field(config, section, 'password', echo=False)
			if password:
				if os.path.isfile(password):
					multiline_print("'{}' exists as a file".format(password))
					# look for corresponding password to username, if any
					credential = ''
					before_password = username+':'
					with open(password, 'r') as f:
						for credential in f:
							if credential.startswith(before_password):
								break
					if credential.startswith(before_password):
						password = credential[len(before_password):]
					else:
						multiline_print(
						"if credentials are to be found in a file, they should",
						"be stored as 'username:password' in this file and you",
						"should let the above username question unanswered")
						raise ValueError('wrong password')
				basename = section
				suffix = 0
				ext = '.credential'
				secret_file = os.path.join(cfg_dir, basename + ext)
				while os.path.exists(secret_file):
					# look for non-existing <basename>-<n>.<ext> filename
					# where <n> is a positive integer
					secret_file = os.path.join(cfg_dir,
						'{}-{}{}'.format(basename, suffix, ext))
					suffix += 1
				msg = "writing new credential file '{}'".format(secret_file)
				if os.path.isfile(secret_file): # should no longer happen
					msg = 'over' + msg
				msgs.append((logging.DEBUG, msg))
				debug_print(msg)
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
					debug_print(msg)
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
					debug_print(msg)
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
		suggestion = section+'.passphrase'
		_pass_, passphrase = query_field(config, section, 'passphrase',
			description='passphrase filename', suggestion=suggestion)
		if not passphrase:
			passphrase = suggestion
		# make passphrase path absolute
		if not os.path.isabs(passphrase):
			if os.path.isfile(passphrase):
				passphrase = os.path.join(os.getcwd(), passphrase)
			else:
				passphrase = os.path.join(cfg_dir, passphrase)
		if os.path.isfile(passphrase):
			# check whether the file is in the configuration directory
			basename, filename = os.path.split(passphrase)
			if basename != cfg_dir:
				# if not, check whether a file with the same name already exists
				new_location = os.path.join(cfg_dir, filename)
				if not os.path.exists(new_location):
					# if not, copy passphrase file into configuration directory
					multiline_print("copying file into configuration directory")
					copyfile(passphrase, new_location)
					passphrase = new_location
		else:
			multiline_print("'{}' file does not exist yet".format(passphrase))
			gen = input(decorate_line('generate a new key? [Y/n] ')).lower()
			if not gen or gen[0] == 'y':
				key = base64.urlsafe_b64encode(os.urandom(32))
				print('{}key: {}'.format(tab, key))
				msg = "writing new passphrase file '{}'".format(passphrase)
				msgs.append((logging.DEBUG, msg))
				with open(passphrase, 'wb') as f:
					f.write(key)
				try:
					os.chmod(passphrase, stat.S_IRUSR | stat.S_IWUSR)
				except OSError as e:
					msg = 'could not change permissions on passphrase file'
					msgs.append((logging.DEBUG, e))
					msgs.append((logging.DEBUG, msg))
					print(e)
					debug_print(msg)
			else:
				msg = "create '{}' file before running {}".format(passphrase, PROGRAM_NAME)
				msgs.append((logging.DEBUG, msg))
				multiline_print(msg)
		config.set(section, _pass_, passphrase)
	## synchronization mode
	config, mode, msgs = query_synchronization_mode(config, section, msgs)
	## refresh rate (let's make it explicit/visible in the configuration file)
	default_refresh = '10'
	_refresh_, refresh = query_field(config, section, 'refresh',
		description='refresh interval (in seconds)', suggestion=default_refresh)
	if not refresh:
		refresh = default_refresh
	config.set(section, _refresh_, refresh)
	## disk quota for webdav
	#if mode != 'download':
	#	help = [[
	#		"quotas on the amount of sent data are recommended for pushers",
	#		" examples:  2GB  4.5G  1To  (default unit is gigabyte)",
	#		]]
	#	_quota_, quota = query_field(config, section, 'quota', help=help)
	#	if quota:
	#		config.set(section, _quota_, quota)
	# delegate to protocol dependent setup
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
			debug_print('aborted.')
		else:
			if type(result) is type(config):
				config = result
	if return_mode:
		return config, mode, msgs
	else:
		return config, msgs


def query_synchronization_mode(config, section, msgs=[]):
	## synchronization mode
	# get existing value, if any
	# and delete all the related options to prevent conflicts
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
			debug_print(msg)
			mode = ''
		else:
			mode = 'upload'
	# ask for mode
	if mode:
		suggestion = mode
	else:
		suggestion = 'shared'
	help = [[
		"synchronization mode can be 'upload', 'download', 'shared' or 'conservative' ",
		tab + ". 'upload': your local files will be sent to the relay repository",
		tab + "            your local files will not be modified",
		tab + ". 'download': you will get files from the relay repository",
		tab + "              your local files will not be sent over the internet",
		tab + "              but they can be modified",
		tab + ". 'shared': your files will be fully synchronized",
		tab + ". 'conservative': your local files will be sent to the relay repository",
		tab + "                  but will not be modified",
		tab + "                  you will get only new files from the relay repository ",
		]]
	multiline_print(help[0][0])
	_mode_, answer = query_field(config, section, 'mode',
			description="which mode for this client?", suggestion=suggestion, help=help)
	# write down (no need to do so with 'shared')
	if answer:
		config.set(section, _mode_, answer)
	elif mode: # `pull only` or `push only` were defined
		# let the original option (almost) untouched
		if pull_only:
			config.set(section, pull_option, 'yes')
		elif push_only:
			config.set(section, push_option, 'yes')
	if mode != 'upload':
		multiline_print("specify the number of pullers for relay repository:",
			"{}'{}'".format(tab, full_address(config, section)))
		while True:
			answer = input(decorate_paragraph(
				"do you want to directly set the puller count [1] or do you ",
				"prefer to be guided with a series of questions [2] so that ",
				"the assistant will choose a value for you? [2] "))
			if not answer or answer in '12':
				break
		guide = answer != '1'
		if guide:
			help = [["specify below the total number of clients for the same ",
				"relay repository"],
				["with no more than two clients or a single puller, you can",
				"safely ignore this question"]]
			# note: 'client count' option is not recognized by :mod:`escale.base.config`
			_count_ = 'client count'
			_, count = query_field(config, section, _count_,
					description="total number of clients",
					help=help)
			if count:
				client_count = int(count)
				config.set(section, _count_, count)
				if mode == 'download':
					heterogeneous = True
				else:
					while True:
						answer = input(decorate_line(
							"will all the clients run in either 'shared' or 'conservative'\nmode? [Y/n] "))
						if not answer or answer.lower()[0] in 'yn':
							break
					heterogeneous = answer and answer.lower()[0] == 'n'
					# note: 'heterogenous clients' option is not recognized
					config.set(section, 'homogeneous clients', 'no' if heterogeneous else 'yes')
				if heterogeneous:
					# note: 'upload count' option is not recognized
					_count_ = 'upload count'
					if mode == 'download':
						suggestion = 1
					else:
						suggestion = 0
					_, count = query_field(config, section, _count_,
							description="number of clients in 'upload' mode",
							suggestion=str(suggestion))
					if count:
						upload_count = int(count)
						config.set(section, _count_, count)
					else:
						upload_count = suggestion
					count = client_count - upload_count
				else:
					count = client_count - 1
				_count_ = actual_option(config, section, fields['count'])
				if _count_:
					existing_count = config.get(section, _count_)
				else:
					_count_ = default_option('count')
					existing_count = None
				if not existing_count or int(existing_count) != count:
					if existing_count:
						msg = "{} was: '{}'; is now: '{}'".format(_count_, existing_count, count)
						msgs.append((logging.INFO, msg))
						multiline_print(msg)
					config.set(section, _count_, str(count))
		else:
			help = [
				["for a given relay repository, pullers are clients that ",
				"may download any file uploaded by another client"],
				["similarly, pushers are clients that may upload files"],
				["the number of pullers is not always predictible ",
				"especially if file access permissions are modified"],
				["it may equal the number of clients that do NOT run in ",
				"'upload' mode"],
				["if all the clients run in 'shared' mode, a safe choice ",
				"is the number of clients minus one"],
				["with no more than two clients or a single puller, you ",
				"can safely ignore this question"],
				]
			_count_, count = query_field(config, section, 'count',
					description="number of pullers", help=help)
	return (config, mode, msgs)


def edit_section(config, cfg_dir, section, msgs=[]):
	'''
	Edit a configuration section.

	Asks for information in the following order:

	* local repository (path)
	* if remote relay:
		* relay host address (no protocol)
		* relay host port (if defined in `config`)
		* relay host directory (if defined in `config`)
	* else if locally accessible relay repository (mount):
		* path to this relay repository
	
	And then delegates to :func:`section_common`.

	Arguments:

		config (ConfigParser): configuration object.

		cfg_dir (str): configuration directory.

		section (str): configuration section name.

		msgs (list): pending messages.

	Returns:

		(ConfigParser, list): updated configuration object and pending messages.
	'''
	# should be silent until call to `query_local_repository`
	msgs.append((logging.DEBUG, "editing the '%s' configuration section", section))
	## retrieve the `protocol` option
	protocol = parse_field(config, section, default_option('protocol', all_options=True))
	# `protocol` may conflict with `address`, but let's resolve this particular case later
	if not protocol:
		addr = parse_field(config, section, fields['address'])
		if addr:
			protocol, _, _, _ = parse_address(addr)
		if protocol:
			config.set(section, default_option('protocol'), protocol)
		else:
			# reroute to `add_section`
			msg = [
				'cannot determine protocol;',
				'configuration section is broken;',
				'trying to overwrite it with a new section',
				]
			msgs.append((logging.INFO, ' '.join(msg)))
			multiline_print(msg)
			return add_section(config, cfg_dir, section, msgs)
	## local repository
	_rep_, rep, msgs = query_local_repository(config, section, msgs)
	config.set(section, _rep_, rep)
	## host address
	remote = protocol not in path_only_protocols
	config, kwargs, msgs = query_relay_address(config, section, remote, msgs)
	return section_common(config, cfg_dir, section, kwargs['protocol'], msgs)




class Service(object):

	__slots__ = [ 'label', 'name', 'protocol', 'address', 'auth', 'rclone_docs', \
		'__dependencies__' ]

	def __init__(self, label, name, protocol=None, address=None, auth=False, rclone_docs=None):
		self.label = label
		self.name = name
		if protocol:
			self.protocol = protocol
		else:
			self.protocol = name
		self.address = address
		self.auth = auth
		if rclone_docs:
			self.rclone_docs = rclone_docs
		else:
			self.rclone_docs = name
		self.__dependencies__ = ['rclone', 'drive']

	def __str__(self):
		requires = self.requires
		if requires:
			entry = '{}\t(requires {})'.format(self.label, quote_join(requires, quote=''))
		else:
			entry = self.label
		return entry

	@property
	def requires(self):
		if isinstance(self.protocol, (tuple, list)):
			return [ p for p in self.protocol if p in self.__dependencies__ ]
		else:
			return [self.protocol] if self.protocol in self.__dependencies__ else []



def simplified_add(config, cfg_dir, section=None, msgs=[]):
	'''
	Add a configuration section.

	Asks for information in the following order:

	* local repository (path)
	* relay service or protocol (display list)
		* if protocol, address of the service
	* disk quota for the relay space (now of limited interest with indexing)
	* indexing with 200MB page size
	
	Some parameters are set or let undefined so that they default to the following settings:

	* no encryption
	* 'shared' synchronization mode
	* refresh time 10s
	* 2GB disk limit for the relay repository

	Arguments:

		config (ConfigParser): configuration object.

		cfg_dir (str): configuration directory.

		section (str): configuration section name.

		msgs (list): pending messages.

	Returns:

		(ConfigParser, list): updated configuration object and pending messages.
	'''
	_local_, local, msgs = query_local_repository(config, section, msgs)
	## service or protocol
	services = [
		Service('Amazon Drive', 'amazoncloud', 'rclone', rclone_docs='amazonclouddrive'),
		Service('Amazon S3', 's3', 'rclone'),
		Service('Backblaze B2', 'b2', 'rclone'),
		Service('Dropbox', 'dropbox', 'rclone'),
		Service('FTP server', 'ftp', auth=True),
		Service('FTPS server', 'ftps', auth=True),
		Service('Google Cloud Storage', 'googlecloud', 'rclone', rclone_docs='googlecloudstorage'),
		Service('Google Drive', 'googledrive', ['rclone', 'drive'], rclone_docs='drive'),
		Service('Hubic', 'hubic', 'rclone'),
		Service('Local disk', 'file', address='localhost'),
		Service('Microsoft OneDrive', 'onedrive', 'rclone'),
		Service('Openstack Swift', 'swift', 'rclone'),
		Service('RClone, any remote', 'rclone', rclone_docs='docs'),
		Service('SSH/SFTP server', 'sftp', 'rclone'),
		Service('WebDAV service', 'https', auth=True),
		Service('Yandex.Disk', 'yandex', 'https', address='webdav.yandex.ru', auth=True),
		]
	multiline_print('choose a number from below:')
	for k, service in enumerate(services):
		print('{:2d} - {}'.format(k+1, service))
	while True:
		service = input(decorate_line('service: '))
		if service:
			try:
				service = services[int(service) - 1]
			except:
				pass
			else:
				break
	if not section:
		section = '{}'.format(service.name)
	address = None
	extra = {}
	if service.requires:
		if not config.has_section(section):
			config.add_section(section)
		existing = dict(config.items(section)) # may include global items
		protocol = None
		for s in service.requires:
			try:
				rclone = importlib.import_module('escale.cli.config.'+s)
				config = rclone.setup(config, section, service=service)
			except ExpressInterrupt:
				raise
			except Exception as e:
				raise
				pass
			else:
				protocol = s
				break
		if protocol is None:
			raise e
		extra = dict(config.items(section))
		for option in existing:
			try:
				if extra[option] == existing[option]:
					del extra[option] 
			except AttributeError:
				pass
	else:
		protocol = service.protocol
		if service.address:
			address = service.address
		else:
			address = None
			while not address:
				address = input(decorate_line('relay host address (required): '))
	if protocol is 'file':
		repository = None
		while not repository:
			repository = input(decorate_line('path to local relay repository (required): '))
	else:
		default = 'Escale Repository'
		repository = input(decorate_line("path to relay repository: [{}] ".format(default)))
		if not repository:
			repository = default
	if service.auth:
		# username
		username = None
		while not username:
			username = input(decorate_line("username for '{}' (required): ".format(address)))
		# password
		password = None
		while not password:
			password = getpass(decorate_line("password for '{}@{}' (required): ".format(username, address)))
		# secret filename
		basename = section
		suffix = 0
		ext = '.credential'
		secret_file = os.path.join(cfg_dir, basename + ext)
		while os.path.exists(secret_file):
			# look for non-existing <basename>-<n>.<ext> filename
			# where <n> is a positive integer
			secret_file = os.path.join(cfg_dir,
				'{}-{}{}'.format(basename, suffix, ext))
			suffix += 1
		# writing secret file
		msg = "writing new credential file '{}'".format(secret_file)
		if os.path.isfile(secret_file): # should no longer happen
			msg = 'over' + msg
		msgs.append((logging.DEBUG, msg))
		debug_print(msg)
		if PYTHON_VERSION == 2: # handle unicode
			if isinstance(username, unicode):
				username = username.encode('utf-8')
			if isinstance(password, unicode):
				password = password.encode('utf-8')
		credential = '{}:{}'.format(username, password)
		with open(secret_file, 'w') as f:
			f.write(credential)
		# changing permissions for secret file
		try:
			os.chmod(secret_file, stat.S_IRUSR | stat.S_IWUSR)
		except OSError as e:
			msg = 'could not change permissions on credential file'
			msgs.append((logging.DEBUG, e))
			msgs.append((logging.DEBUG, msg))
			debug_print(msg)
	# writing configuration file
	if config.has_section(section):
		msg = "overwriting section '{}'".format(section)
		msgs.append((logging.DEBUG, msg))
		debug_print(msg)
		config.remove_section(section)
	config.add_section(section)
	config.set(section, _local_, local)
	config.set(section, default_option('protocol'), protocol)
	if address:
		config.set(section, default_option('address'), address)
	for option in extra:
		config.set(section, option, extra[option])
	config.set(section, default_option('directory'), repository)
	if service.auth:
		config.set(section, 'secret file', secret_file)
	config.set(section, default_option('mode'), 'shared')
	config.set(section, default_option('refresh'), '10')
	config.set(section, default_option('quota'), '2GB')
	if _indexing(protocol):
		# new in 0.7: indexing is default behaviour
		config.set(section, default_option('index'), '1')
		config.set(section, default_option('maxpagesize'), '200MB')
	# new in 0.7.1: checksum caching is default behaviour
	config.set(section, default_option('checksumcache'), 'on')
	return config, msgs

