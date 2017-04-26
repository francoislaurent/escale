# -*- coding: utf-8 -*-

from syncacre.base.config import *
import os
import stat
import logging
from getpass import *
import base64

try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass

tab = "\t"


def query_field(config, section, field, description=None, suggestion='', required=False, echo=True):
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
		if not suggestion:
			suggestion = existing
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
	config, cfg_file, msgs = parse_cfg(cfg_file, msgs, True)
	cfg_dir = os.path.dirname(cfg_file)
	if cfg_dir == global_cfg_dir: # superuser mode
		cfg_dir = os.path.join(global_cfg_dir, SYNCACRE_NAME) # /etc/syncacre
		if not os.path.isdir(cfg_dir):
			if os.path.exists(cfg_dir):
				raise RuntimeError("'{}' should be a directory".format(cfg_dir))
				os.unlink(cfg_dir)
			os.mkdir(cfg_dir)
		_log_file_ = 'log file'
		try:
			log_file = config.get(section, _log_file_)
		except:
			log_file = None
		else:
			if log_file.startswith(global_cfg_dir):
				msg = "logging in '{}' is not permitted; fixing '{}'".format(global_cfg_dir, _log_file_)
				msgs.append((logging.DEBUG, msg))
				print(msg)
				log_file = None
		if not log_file:
			log_file = '/var/log/{}.log'.format(SYNCACRE_NAME)
			config.set(default_section, _log_file_, log_file)
	msg = "editing configuration file '{}'".format(cfg_file)
	msgs.append((logging.DEBUG, msg))
	print(msg)
	while True:
		sections = config.sections()
		if sections:
			print("existing section(s):")
			for section in sections:
				print("{}. '{}'".format(tab, section))
		section = input('section name (required): ')
		new = section not in sections
		if new:
			config.add_section(section)
		# client name
		_client_, client = query_field(config, section, 'clientname')
		if client:
			config.set(section, _client_, client)
		# host address
		_addr_, addr = query_field(config, section, 'address', required=True)
		config.set(section, _addr_, addr)
		# secret
		# username
		secret_file = None
		print('if the credentials are available in a file, leave the following field empty')
		_username_, username = query_field(config, section, 'username')
		if username:
			# password
			_, password = query_field(config, section, 'password', echo=False)
			if password:
				if os.path.isfile(password):
					print("'{}' exists as a file".format(password))
					print("if credentials are to be found in a file, they should be provided as `username:password`")
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
				with open(secret_file, 'w') as f:
					f.write('{}:{}'.format(username, password))
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
			_, secret_file = query_field(config, section, 'password', description='secret file')
			if not os.path.isabs(secret_file):
				if os.path.isfile(secret_file):
					secret_file = os.path.join(os.getcwd(), secret_file)
				else:
					secret_file = os.path.join(cfg_dir, secret_file)
			if not os.path.isfile(secret_file):
				msg = "'{}' file does not exist yet; create it before running {}".format(secret_file, SYNCACRE_NAME)
				msgs.append((logging.DEBUG, msg))
				print(msg)
		# encryption
		_enc_, encryption = query_field(config, section, 'encryption', suggestion='on')
		if encryption:
			encryption = encryption.lower()
		else:
			encryption = 'on'
		config.set(section, _enc_, encryption)
		# encryption passphrase
		if not any([ encryption == b for b in [ '0', 'off', 'no', 'false' ] ]):
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
					msg = "create '{}' file before running {}".format(passphrase, SYNCACRE_NAME)
					msgs.append((logging.DEBUG, msg))
					print(msg)
			config.set(section, _pass_, passphrase)
		# pull/push only
		pull_push = input("should the client either pull or push? [pull/push/BOTH] ")
		if pull_push:
			pull_push = pull_push.lower()
			if pull_push == 'pull':
				config.set(section, 'pull only', 'yes')
			elif pull_push == 'push':
				config.set(section, 'push only', 'yes')
		# refresh rate
		_refresh_, refresh = query_field(config, section, 'refresh')
		if refresh:
			config.set(section, _refresh_, refresh)
		# stop
		if not input('do you want to add/edit another section? [y/N] ').lower().startswith('y'):
			break
	# write configuration
	with open(cfg_file, 'w') as f:
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
	return msgs

