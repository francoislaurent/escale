# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import subprocess
import sys
import os
import traceback

from escale import *
from escale.base.essential import *
from escale.base.config import *
from escale.relay.info import *
from escale.manager.access import *
from escale.base.launcher import *
from escale.manager.migration import *
from escale.manager.backup import *


def start(pidfile=None):
	"""
	Start all the client defined in the default configuration file.

	This routine is the only one that records the pid of the main process in file.
	"""
	if not pidfile:
		pidfile = get_pid_file()
	if os.path.exists(pidfile):
		print("{} is already running; if not, delete the '{}' file".format(PROGRAM_NAME, pidfile))
		return 1
	try:
		import daemon
		import daemon.pidfile
	except ImportError:
		python = sys.executable
		if python is None:
			if PYTHON_VERSION == 3:
				python = 'python3'
			else:
				python = 'python'
		sub = subprocess.Popen([python, '-m', PROGRAM_NAME, '-r'])
		with open(pidfile, 'w') as f:
			f.write(str(sub.pid))
	else:
		with daemon.DaemonContext(working_directory=os.getcwd(),
				pidfile=daemon.pidfile.TimeoutPIDLockFile(pidfile)):
			escale_launcher()
	return 0


def stop(pidfile=None):
	"""
	Kill all the running escale processes.
	"""
	if not pidfile:
		pidfile = get_pid_file()
	if not os.path.exists(pidfile):
		print("{} is not running".format(PROGRAM_NAME))
		return 1
	with open(pidfile, 'r') as f:
		pid = str(f.read())
	p = subprocess.Popen(['ps', '-eo', 'ppid,pid'], stdout=subprocess.PIPE)
	ps = p.communicate()[0]
	children = []
	for line in ps.splitlines():
		ppid, cpid = line.split()
		if ppid == pid:
			children.append(cpid)
	for child in children:
		subprocess.call(['kill', child])
	subprocess.call(['kill', pid])
	if PYTHON_VERSION == 3: # repeat
		time.sleep(1)
		subprocess.call(['kill', pid])
	os.unlink(pidfile)


def access(modifiers=None, resource=None, repository=None):
	"""
	Get or set access modifiers of a resource.
	"""
	get_modifiers = modifiers is None
	set_modifiers = modifiers is not None
	if resource and os.path.exists(resource):
		if not os.path.isabs(resource):
			resource = join(os.getcwd(), resource)
	cfg, _, _ = parse_cfg()
	if repository is None:
		repositories = cfg.sections()
	elif isinstance(repository, (list, tuple)):
		repositories = repository
	else:
		repositories = [repository]
	mmap1 = {'?': None, '+': True, '-': False}
	mmap2 = { mmap1[k]: k for k in mmap1 }
	ok = False
	for rep in repositories:
		args = parse_fields(cfg, rep, fields)
		persistent = get_cache_file(config=cfg, section=rep, prefix=access_modifier_prefix)
		if get_modifiers and not os.path.exists(persistent):
			continue
		ctl = AccessController(rep, persistent=persistent, create=set_modifiers, **args)
		if set_modifiers:
			assert ctl.persistent
			set = dict(r=ctl.setReadability, w=ctl.setWritability)
			for mode in set:
				if mode in modifiers:
					i = modifiers.index(mode) + 1
					try:
						p = modifiers[i]
					except IndexError:
						p = True
					else:
						p = mmap1[p]
					try:
						set[mode](resource, p)
					except OSError as e:
						#print(e)
						pass
					else:
						ok = True
		if get_modifiers:
			try:
				modifiers = 'r{}w{}'.format(mmap2[ctl.getReadability(resource)],
						mmap2[ctl.getWritability(resource)])
			except Exception as e:
				#print(e) # TODO: identify which exception
				pass
			else:
				ok = not ok
				if not ok:
					break
	if ok:
		if get_modifiers:
			return modifiers
	else:
		if set_modifiers or not modifiers:
			raise OSError("cannot find file '{}'".format(resource))
		elif get_modifiers:
			raise ValueError("'{}' found in multiple repositories".format(resource))


def migrate(repository=None, destination=None, fast=None):
	"""
	Migrate a relay repository from a host to another.

	Supports change in protocol and prefixes/suffixes of special files.
	"""
	kwargs = {}
	if os.path.isfile(destination):
		changes = parse_cfg(destination)
		repositories = changes.sections()
		if repository:
			if repository in repositories:
				for r in repositories:
					if r != repository:
						changes.remove_section(r)
			else:
				raise ValueError('cannot change repository name')
	else:
		protocol, address, port, path = parse_address(destination)
		if not protocol:
			raise ValueError('relay host address should include protocol')
		if not repository:
			config, _, _ = parse_cfg()
			repository = config.sections()
			if repository[1:]:
				raise ValueError("several repositories defined; please specify with '--repository'")
			repository = repository[0]
			kwargs['config'] = config
		changes = ConfigParser()
		changes.add_section(repository)
		changes.set(repository, default_option('protocol'), protocol)
		if address:
			changes.set(repository, default_option('address'), address)
		if port:
			changes.set(repository, default_option('port'), port)
		if path:
			changes.set(repository, default_option('dir'), path)
	if fast:
		kwargs['safe'] = False
	migrate_repositories_and_update_config(changes, **kwargs)


def backup(repository=None, archive=None, fast=None):
	"""
	Store a full relay repository in an archive.
	"""
	kwargs = {}
	if fast:
		kwargs['safe'] = False
	backup_manager(archive, repository, 'backup', **kwargs)


def restore(repository=None, archive=None, fast=None):
	"""
	Overwrite a relay repository with the uncompressed content of an archive.
	"""
	kwargs = {}
	if fast:
		kwargs['safe'] = False
	backup_manager(archive, repository, 'restore', **kwargs)


def recover(repository=None, timestamp=None, overwrite=True):
	"""
	Make a relay repository with placeholder files as if the local repository
	resulted from a complete download of an existing repository with escale.
	"""
	if timestamp:
		tsformat = timestamp
	else:
		tsformat = '%y%m%d_%H%M%S'
	cfg, cfg_file, msgs = parse_cfg()
	logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
	flush_init_messages(logger, msgs)
	if repository:
		repositories = [ repository ]
	else:
		repositories = cfg.sections()
	fd, local_placeholder = tempfile.mkstemp()
	os.close(fd)
	try:
		for repository in repositories:
			try:
				client = make_client(cfg, repository)
				ls = client.repository.listFiles()
				client.relay.open()
				for local in ls:
					remote = os.path.relpath(local, client.repository.path)
					remote_placeholder = client.relay.placeholder(remote)
					if client.relay.hasPlaceholder(remote):
						if overwrite:
							client.relay.unlink(remote_placeholder)
						else:
							continue
					checksum = None
					if client.hash_function:
						timestamp = os.path.getmtime(local)
						content = client.encryption.encrypt(local)
						try:
							with open(content, 'rb') as f:
								checksum = client.hash_function(f.read())
						finally:
							client.encryption.finalize(content)
					if checksum:
						metadata = repr(Metadata(pusher=client.relay.client,
								target=remote, timestamp=timestamp,
								checksum=checksum))
					else:
						# old format
						timestamp = time.strftime(tsformat,
								time.gmtime(os.path.getmtime(local)))
						metadata = timestamp
					with open(local_placeholder, 'w') as f:
						f.write(metadata)
					client.relay._push(local_placeholder, remote_placeholder)
				client.relay.close()
			except:
				print(traceback.format_exc())
	finally:
		os.unlink(local_placeholder)

