# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import *
from escale.log.log import *
from escale.base.config import *
from escale.manager.config import *
from escale.relay.index import AbstractIndexRelay
import os
import logging
try:
	from configparser import ConfigParser, NoSectionError # Py3
except ImportError:
	import ConfigParser as cp
	ConfigParser = cp.SafeConfigParser
	NoSectionError = cp.NoSectionError
import tempfile


def migrate_repositories_and_update_config(changes, config=None, safe=True, logger=None):
	"""
	Migrate relay repositories and update configuration file.

	Arguments:

		changes (ConfigParser): changes to apply to relays.

		config (str or ConfigParser): configuration for active relays.

		safe (bool): whether to lock all the resources or not.

		logger (Logger): logger.

	"""
	# load configuration file
	if isinstance(config, ConfigParser):
		cfg_file = config.filename
		msgs = []
	else:
		config, cfg_file, msgs = parse_cfg(config)
	# set logger
	if logger is None:
		logger, msgs = set_logger(config, cfg_file, msgs=msgs)
	# flush messages
	flush_init_messages(logger, msgs)
	# migrate repositories
	for repository in changes.sections():
		repository_logger = logger.getChild(repository)
		repository_logger.setLevel(logging.DEBUG)
		config = migrate_repository(repository, changes, config, safe,
				logger=repository_logger)
	# update configuration file
	write_config(cfg_file, config)


def migrate_repository(repository, changes, config=None, safe=True, logger=None):
	"""
	Parse the configuration sections for the source and destination relays and transfer
	the entire repository from the source relay to the destination relay.

	Expected options in `changes` are relay protocol (required), relay address, relay port,
	path of the relay repository and credentials.

	Client name or the encryption parameters cannot be modified at migration time.

	Arguments:

		repository (str): configuration section.

		changes (ConfigParser): configuration object with a section corresponding to
			`repository`.

		config (str or ConfigParser): configuration file or object for the source relay.

		safe (bool or (bool, bool)): whether to lock all the resources before transfer;
			the argument is passed directly to `inter_relay_copy`.

		logger (Logger): logger.

	Returns:

		ConfigParser: updated configuration object for the migrated and other active relays.
	"""
	if logger is None:
		raise NotImplementedError
	# parse config
	try:
		relay_src, base_args = parse_section(config, repository, logger)
	except NoSectionError:
		logger.error("no such repository: '%s'", repository)
		return
	# parse changes
	relay_dest, changes = parse_section(changes, repository, logger)
	if changes['clientname'] == repository:
		# if default value, then ignore it
		del changes['clientname']
	# check consistency for a few fields
	not_mutable = [ 'clientname', 'encryption', 'passphrase' ]
	for field in not_mutable:
		if field in changes:
			if not (field in base_args and changes[field] == base_args[field]):
				logger.warning("cannot modify %s at migration time; ignoring the new value", field)
			del changes[field]
	# clear a few unrelevant extra fields
	client = base_args.pop('clientname')
	remove_fields = [ 'passphrase', 'encryption', 'path', 'mode', 'refresh', 'quota', 'maintainer' ]
	for field in remove_fields:
		try:
			del base_args[field]
		except KeyError:
			pass
		try:
			del changes[field]
		except KeyError:
			pass
	# set arguments for the destination relay
	new_args = dict(base_args) # copy
	new_args.update(changes)
	# make loggers
	logger_src = logger.getChild('src')
	logger_src.setLevel(logging.DEBUG)
	logger_dest = logger.getChild('dest')
	logger_dest.setLevel(logging.DEBUG)
	# make relays
	addr_src = base_args.pop('address')
	relay_dir_src = base_args.pop('directory')
	relay_src = relay_src(client, addr_src, relay_dir_src, logger=logger_src,
			**base_args)
	addr_dest = new_args.pop('address')
	relay_dir_dest = new_args.pop('directory')
	relay_dest = relay_dest(client, addr_dest, relay_dir_dest, logger=logger_dest,
			**new_args)
	# connect
	relay_src.open(), relay_dest.open()
	# copy
	to_fix = inter_relay_copy(relay_src, relay_dest, safe=safe)
	if to_fix:
		logger.info('\n\t'.join(['the following files could not be transfered: ']+to_fix))
	# update and return config
	extra = changes.pop('config', {})
	for field in extra:
		if field not in changes:
			changes[field] = extra[field]
	for field in changes:
		try:
			option = actual_option(config, repository, fields[field])
		except KeyError:
			option = field
		config.set(repository, option, changes[field])
	return config


def _acquire_lock(relay, resource, blocking=True):
	try:
		return relay.acquireLock(resource, blocking=blocking)
	except ExpressInterrupt:
		raise
	except:
		return False

def _release_lock(relay, resource):
	try:
		relay.releaseLock(resource)
	except ExpressInterrupt:
		raise
	except:
		return False
	else:
		return True

def _get(relay, src, dest):
	try:
		return relay._get(src, dest) is not False
	except ExpressInterrupt:
		raise
	except:
		relay.logger.info("read failed: '%s'", src)
		return False

def _push(relay, src, dest):
	try:
		return relay._push(src, dest) is not False
	except ExpressInterrupt:
		raise
	except:
		relay.logger.info("write failed: '%s'", dest)
		return False


def inter_relay_copy(src_relay, dest_relay, safe=True, overwrite=False, files=[]):
	"""
	Transfer files from a source relay to a destination relay.

	Files are locally downloaded from the source and then 
	uploaded to the destination one after the other.

	Regular files in the source repository are all locked both on the
	source relay and destination relay before any transfer begins, and
	they are all released at the very end.

	.. note:: relays should implement :class:`~escale.relay.relay.Relay`
		instead of :class:`~escale.relay.relay.AbstractRelay`

	In a future release, this function will also translate the names of
	the special files according to prefixes and suffixes defined in the 
	relay objects.

	Arguments:

		src_relay (escale.relay.Relay): source opened relay.

		dest_relay (escale.relay.Relay): destination opened relay.

		safe (bool or (bool, bool)): if ``True``, lock the regular files before operating;
			if a tuple, the first boolean applies to the source relay and the second
			one applies to the destination relay.

		overwrite (bool): overwrite existing locks on destination relay;
			you should ensure yourself that the destination repository is inactive.

		files (list of str): list of paths in the source repository;
			default behavior consists of transfering the entire repository tree.

	Returns:

		list of str: list of paths for files that could not be successfully transfered.

	.. note:: instead of setting `overwrite` to `True`, it would preferable to purge
		the destination repository.
	"""
	if isinstance(safe, tuple):
		try:
			src_safe = safe[0]
		except IndexError:
			src_safe = True
		try:
			dest_safe = safe[1]
		except IndexError:
			dest_safe = src_safe
	else:
		src_safe = safe
		dest_safe = safe
	# index support (added in 0.7.1)
	if isinstance(src_relay, AbstractIndexRelay) and isinstance(dest_relay, AbstractIndexRelay):
		# with indices, `safe` should always be True, and `overwrite` is ignored (considered to be True)
		if files:
			raise NotImplementedError('cannot select a subset of files in indices')
		for page in src_relay.listPages():
			if src_safe and not src_relay.acquirePageLock(page):
				# TODO: log failure
				continue
			try:
				if dest_safe and not dest_relay.acquirePageLock(page):
					# TODO: log failure
					continue
				fd, tmp = tempfile.mkstemp()
				os.close(fd)
				try:
					# IndexRelay only
					files = []
					files.append(src_relay.persistentIndex(page))
					if src_relay.hasUpdate(page):
						files.append(src_relay.updateIndex(page, mode='r'))
						files.append(src_relay.updateData(page, mode='r'))
					for location in files:
						src_relay.base_relay._get(location, tmp)
						dest_relay.base_relay._push(tmp, location)
				finally:
					os.unlink(tmp)
					if dest_safe:
						dest_relay.releasePageLock(page)
			finally:
				if src_safe:
					src_relay.releasePageLock(page)
		return []
	# standard (no index) relays
	new_placeholders = not (src_relay._placeholder_prefix == dest_relay._placeholder_prefix \
			and src_relay._placeholder_suffix == dest_relay._placeholder_suffix)
	new_locks = not (src_relay._lock_prefix == dest_relay._lock_prefix \
			and src_relay._lock_suffix == dest_relay._lock_suffix)
	new_messages = not (src_relay._message_prefix == dest_relay._message_prefix \
			and src_relay._message_suffix == dest_relay._message_suffix)
	if not (src_relay._message_hash is None and dest_relay._message_hash is None):
		fd, filename = tempfile.mkstemp(text=True)
		os.write(fd, 'test content')
		os.close(fd)
		try:
			new_messages |= src_relay._message_hash(filename) != dest_relay._message_hash(filename)
		finally:
			os.unlink(filename)
	if new_placeholders or new_locks or new_messages:
		raise NotImplementedError('name translation for special files is not implemented yet')
	# initialize variables
	groups = {}
	status = {}
	files_to_fix = []
	INITIALLY_LOCKED = -1
	# list files in source repository
	if not files:
		files = src_relay._list()
		ls = dest_relay._list()
		# `ls` is either a list or an iterator
		if isinstance(ls, list):
			ls = iter(ls)
		try:
			ls.next()
		except StopIteration:
			pass
		else:
			dest_relay.logger.warning('repository is not empty')
	# group them by regular file
	for f in files:
		if src_relay.isSpecial(f):
			_f = src_relay.fromSpecial(f)
			if src_relay.isLock(f):
				status[_f] = INITIALLY_LOCKED
		else:
			_f = f
		try:
			groups[_f].append(f)
		except KeyError:
			groups[_f] = [f]
	try:
		# lock all the resources both on the source relay and on the destination relay
		for f in groups:
			if status.get(f, src_safe): # status contains only Falses
				src_relay.logger.debug("locking '%s'", f)
				status[f] = _acquire_lock(src_relay, f, blocking=False)
			if dest_safe:
				dest_relay.logger.debug("locking '%s'", f)
				if not _acquire_lock(dest_relay, f, blocking=False):
					if overwrite:
						# this is unsafe
						dest_relay.unlink(dest_relay.lock(f))
						_acquire_lock(dest_relay, f, blocking=True)
					else:
						# destination relay should be inactive
						raise RuntimeError('cannot lock resource on destination relay')
		# transfer files
		cache = src_relay.newTemporaryFile()
		# begin with secured resources
		for g in groups:
			if status.get(g, True) is True:
				for f in groups[g]:
					src_relay.logger.debug("transferring '%s'", f)
					if not (_get(src_relay, f, cache) and _push(dest_relay, cache, f)):
						files_to_fix.append(f)
		# try now with unsecured resources
		for g in groups:
			if status.get(g, True) is True:
				continue # skip secured
			elif status[g] is False:
				# locking failed; try again
				src_relay.logger.debug("locking '%s'", g)
				status[g] = _acquire_lock(src_relay, f, blocking=True)
			for f in groups[g]:
				src_relay.logger.debug("transferring '%s'", f)
				if not (_get(src_relay, f, cache) and _push(dest_relay, cache, f)):
					files_to_fix.append(f)
	finally:
		msg = "reverting changes; please do not interrupt now"
		if src_safe:
			src_relay.logger.info(msg)
		if dest_safe:
			dest_relay.logger.info(msg)
		# release locks on destination relay
		if dest_safe:
			for f in groups:
				if not _release_lock(dest_relay, f):
					dest_relay.logger.error("lock for '%s' might not have been released", f)
			dest_relay.logger.info("done")
		# release locks in source relay
		if src_safe:
			for f in groups:
				if status.get(f, INITIALLY_LOCKED) is not INITIALLY_LOCKED:
					if not _release_lock(src_relay, f):
						src_relay.logger.error("lock for '%s' might not have been released", f)
			src_relay.logger.info("done")
	return files_to_fix

