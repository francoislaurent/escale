# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# Copyright © 2017, François Laurent
#      Contribution: documentation, update timestamp, encryption, listing cooldown,
#      complete rewrite with the introduction of AbstractIndexRelay, IndexUpdate, UpdateRead, UpdateWrite

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import *
from .relay import *
from .info import *
import time
import calendar
import itertools
import traceback
import tarfile
import tempfile
import shutil
import bz2
import os
from collections import defaultdict, MutableMapping


class AbstractIndexRelay(AbstractRelay):

	def loaded(self, page):
		raise NotImplementedError('abstract method')

	def clearIndex(self):
		raise NotImplementedError('abstract method')

	def listPages(self):
		raise NotImplementedError('abstract method')

	def getPageIndex(self, page):
		raise NotImplementedError('abstract method')

	def hasUpdate(self, page):
		raise NotImplementedError('abstract method')

	def getUpdate(self, page, terminate=None):
		return UpdateRead(self, page, terminate)

	def getUpdateIndex(self, page, sync=True):
		raise NotImplementedError('abstract method')

	def getUpdateData(self, page, destination):
		raise NotImplementedError('abstract method')

	def setUpdate(self, page):
		return UpdateWrite(self, page)

	def setUpdateIndex(self, page, index, sync=True):
		raise NotImplementedError('abstract method')

	def setUpdateData(self, page, data):
		raise NotImplementedError('abstract method')

	def consumeUpdate(self, page, terminate):
		raise NotImplementedError('abstract method')

	def requestMissing(self, page):
		raise NotImplementedError('abstract method')

	def repairUpdates(self):
		raise NotImplementedError('abstract method')

	def acquirePageLock(self, page, mode=None):
		raise NotImplementedError('abstract method')

	def releasePageLock(self, page):
		raise NotImplementedError('abstract method')


class IndexUpdate(MutableMapping):

	def __init__(self, relay, page, mode):
		self.relay = relay
		self.page = page
		self.content = {}
		self.mode = mode

	@property
	def logger(self):
		return self.relay.logger

	def __enter__(self):
		if not self.relay.acquirePageLock(self.page, self.mode):
			raise PostponeRequest("failed to lock page '%s'", self.page)
		return self

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
		try:
			self.relay.releasePageLock(self.page)
		except:
			if exc_type is None:
				self.relay.logger.warning("missing lock for page '%s'", self.page)

	def __iter__(self):
		return self.content.__iter__()

	def __getitem__(self, resource):
		return self.content[resource]

	def __len__(self):
		return len(self.content)

	def __setitem__(self, resource, metadata):
		self.content[resource] = metadata

	def __delitem__(self, resource):
		del self.content[resource]


class UpdateRead(IndexUpdate):

	def __init__(self, relay, page, terminate):
		IndexUpdate.__init__(self, relay, page, 'r')
		self.terminate = terminate

	def __enter__(self):
		if not self.relay.loaded(self.page) or self.relay.hasUpdate(self.page):
			IndexUpdate.__enter__(self)
			self.content = self.relay.getUpdateIndex(self.page)
			if not self.content:
				IndexUpdate.__exit__(self, None, None, None)
				raise PostponeRequest("no update for page '%s'", self.page)
		else:
			raise PostponeRequest
		return self

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
		self.relay.consumeUpdate(self.page, self.terminate)
		IndexUpdate.__exit__(self, exc_type, *args)


class UpdateWrite(IndexUpdate):

	def __init__(self, relay, page):
		IndexUpdate.__init__(self, relay, page, 'w')

	def __enter__(self):
		if self.relay.hasUpdate(self.page):
			raise PostponeRequest
		return IndexUpdate.__enter__(self)

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
		if self.content:
			self.relay.setUpdateIndex(self.page, self.content)
		IndexUpdate.__exit__(self, exc_type, *args)



group_begin_breaker = '---group---'
group_end_breaker = '-----------'

puller_breaker = '---pullers---'


def write_index(filename, metadata, pullers=[], compress=False, groupby=[]):
	"""
	Write index to file.
	"""
	if compress:
		_open = bz2.BZ2File
	else:
		_open = open
	if groupby:
		_metadata = defaultdict(dict)
		for resource in metadata:
			mdata = metadata[resource]
			if isinstance(mdata, Metadata):
				mdata = repr(mdata)
			if not isinstance(mdata, (tuple, list)):
				mdata = mdata.splitlines()
			# sort out grouping keys
			_mdata = []
			group = {}
			for line in mdata:
				_groupby = None
				for g in groupby:
					if line.startswith(g):
						_groupby = g
						break
				if _groupby:
					group[_groupby] = line
				else:
					_mdata.append(line)
			# sort grouping keys
			_group = []
			for g in groupby:
				try:
					_group.append(group[g])
				except KeyError:
					pass
			#
			_metadata[tuple(_group)][resource] = '\n'.join(_mdata)
	else:
		for resource in metadata:
			mdata = metadata[resource]
			if isinstance(mdata, Metadata):
				metadata[resource] = repr(mdata)
		_metadata = dict(default=metadata)
	with _open(filename, 'w') as f:
		if compress:
			def write(s):
				f.write(asbytes(s))
		else:
			write = f.write
		for group in _metadata:
			if groupby:
				write(group_begin_breaker+'\n')
				for line in group:
					write(line+'\n')
				write(group_end_breaker+'\n')
			metadata = _metadata[group]
			for resource in metadata:
				mdata = metadata[resource]
				if mdata:
					if not mdata.endswith('\n'):
						mdata += '\n'
				else:
					mdata = '' # string
				nchars = len(mdata)
				write('{} {}\n{}'.format(resource, nchars, mdata))
		if pullers:
			write(puller_breaker)
			for reader in pullers:
				write('\n'+reader)

def read_index(filename, compress=False, groupby=[]):
	"""
	Read index from file.
	"""
	metadata = {}
	if groupby:
		read_group_def = False
	else:
		group = ''
	pullers = []
	if compress:
		_open = bz2.BZ2File
	else:
		_open = open
	with _open(filename, 'r') as f:
		while True:
			line = asstr(f.readline().rstrip()) # asstr is necessary with compression
			if not line:
				break
			if groupby:
				if line == group_begin_breaker:
					read_group_def = True
					group = []
					continue
				elif line == group_end_breaker:
					read_group_def = False
					if group:
						group = '\n'.join(group)+'\n'
					else:
						group = ''
					continue
				elif read_group_def:
					group.append(line)
					continue
			has_pullers = line == puller_breaker
			if has_pullers:
				break
			resource, nchars = line.rsplit(None, 1)
			nchars = int(nchars)
			if nchars:
				metadata[resource] = group+asstr(f.read(nchars))
			else:
				metadata[resource] = None
		if has_pullers:
			while line:
				line = asstr(f.readline())
				pullers.append(line.rstrip())
	return (metadata, pullers)



class IndexRelay(AbstractIndexRelay):
	"""
	Index-based relay.

	:class:`RelayIndex` plays both :class:`AbstractRelay` and (part of) :class:`Manager` roles.

	Repository content is indexed.
	It consists of a comprehensive index and an update.

	An update stores files in a compressed archive and is accompanied by an index that lists the content
	of the archive.

	The total archive is encrypted instead of the individual files.

	Indexing potentially supports paging. See also the :meth:`page` method.
	"""

	def __init__(self, *args, **kwargs):
		base = kwargs.pop('base', Relay)
		#lock_args = kwargs.pop('lock_args', {})
		self.base_relay = base(*args, **kwargs)
		#self.lock_args = lock_args
		self.lock_args = {}
		self.locked = {}
		self.transaction_timestamp = None
		self.index = {}
		self.index_mtime = {}
		self.last_update = {}
		self.last_update_cache = {}
		self.listing_time = None
		self.listing_cache = None
		self.listing_cooldown = 5
		#
		self._persistent_index_prefix = '.'
		self._persistent_index_suffix = '.index'
		# update indices should be clearly differentiated from persistent indices;
		# if they exhibit the same prefix and suffix, then update indices should
		# have a timestamp in their name (_timestamp_update = True) and pages
		# should not have any dot (.) in their name
		self._update_index_prefix = '.'
		self._update_index_suffix = '.index'
		self._timestamp_index = True
		#
		self._update_data_prefix = '.'
		self._update_data_suffix = '.data'
		self._timestamp_data = True
		# compress index
		self.metadata_group_by = ['placeholder', 'pusher']

	@property
	def logger(self):
		return self.base_relay.logger

	@property
	def ui_controller(self):
		return self.base_relay.ui_controller

	@property
	def client(self):
		return self.base_relay.client

	@property
	def address(self):
		return self.base_relay.address

	@property
	def repository(self):
		return self.base_relay.repository

	@client.setter
	def client(self, name):
		self.base_relay.client = name

	def page(self, remote_file):
		"""
		Page key/name.

		Hash function for paging of files by remote path.

		Arguments:

			remote_file (str): path to file.

		Returns:

			str: page key/name.
		"""
		return '0'

	def persistentIndex(self, page):
		return '{}{}{}'.format(self._persistent_index_prefix, page, self._persistent_index_suffix)

	def updateIndex(self, page, mode=None):
		if self._timestamp_index:
			ts = self.updateTimestamp(page, mode=mode)
			if ts:
				ts = '.{}'.format(ts)
			else:
				return None
		else:
			ts = ''
		return '{}{}{}{}'.format(self._update_index_prefix, page, ts, self._update_index_suffix)

	def updateData(self, page, mode=None):
		if self._timestamp_data:
			ts = self.updateTimestamp(page, mode=mode)
			if ts:
				ts = '.{}'.format(ts)
			else:
				return None
		else:
			ts = ''
		return '{}{}{}{}'.format(self._update_data_prefix, page, ts, self._update_data_suffix)

	def updateTimestamp(self, page, mode=None):
		timestamp = None
		if self._timestamp_index:
			if mode == 'w':
				if not self.transaction_timestamp:
					self.transaction_timestamp = int(round(time.time()))
				timestamp = self.transaction_timestamp
			elif mode is None or mode == 'r':
				ls = self.listing_cache # should be up-to-date
				prefix1 = '{}{}.'.format(self._update_index_prefix, page)
				prefix2 = '{}{}.'.format(self._update_data_prefix, page)
				ls1 = [ l[len(prefix1):] for l, _ in ls if l.startswith(prefix1) ]
				ls2 = [ l[len(prefix2):] for l, _ in ls if l.startswith(prefix2) ]
				if self._update_index_suffix:
					suffix_len = len(self._update_index_suffix)
					ls1 = [ l[:-suffix_len] for l in ls1 if l.endswith(self._update_index_suffix) ]
				if self._update_data_suffix:
					suffix_len = len(self._update_data_suffix)
					ls2 = [ l[:-suffix_len] for l in ls2 if l.endswith(self._update_data_suffix) ]
				ts = []
				for l in ls1+ls2:
					try:
						ts.append(int(l))
					except ValueError:
						pass
				if ts:
					if 1 < len(set(ts)):
						msg = "multiple update indices for page '{}'".format(page)
						self.logger.critical(msg)
						raise RuntimeError(msg)
					timestamp = ts[0]
			else:
				msg = "mode should be either 'r' (read or download) or 'w' (write or upload)"
				self.logger.critical(msg)
				raise NotImplementedError(msg)
		else:
			reffile = self.persistentIndex(page)
			for filename, mtime in self.listing_cache:
				if filename == reffile:
					timestamp = int(round(calendar.timegm(mtime)))
		return timestamp

	@property
	def listing_cache(self):
		return self.base_relay.listing_cache

	@listing_cache.setter
	def listing_cache(self, cache):
		self.base_relay.listing_cache = cache

	def remoteListing(self):
		self.base_relay.remoteListing()

	def refreshListing(self, remote_dir='', force=False):
		now = time.time()
		if force or not (self.listing_time and now - self.listing_time < self.listing_cooldown):
			#self.listing_cache = list(self.base_relay._list(remote_dir, recursive=False, stats=('mtime',)))
			self.remoteListing()
			self.listing_time = now

	def clearIndex(self):
		for page in self.listPages():
			#if not self.acquirePageLock(page, 'r'):
			#	self.logger.warning("cannot lock page '%s'", page)
			#	continue
			#tmp = self.base_relay.newTemporaryFile()
			try:
				#self.base_relay._get(self.persistentIndex(page), tmp)
				#self.index[page], _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
				#self.index_mtime[page] = [ mtime for name, mtime in self.listing_cache if name == self.persistentIndex(page) ][0]
				del self.index[page]
				del self.index_mtime[page]
			except KeyError:
				pass
			#finally:
			#	self.base_relay.delTemporaryFile(tmp)
			#	try:
			#		self.releasePageLock(page)
			#	except:
			#		self.logger.debug("missing lock for page '%s'", page)

	def loaded(self, page, mtime=None, check_mtime=True):
		if page in self.index:
			if not check_mtime:
				return True
			persistent_index = self.persistentIndex(page)
			if self.base_relay.exists(persistent_index):
				assert self.index_mtime[page] is not None
				if not mtime:
					mtime = [ mtime for name, mtime in self.listing_cache \
							if name == persistent_index ]
					if mtime:
						mtime = mtime[0]
				if mtime:
					t1 = mtime
					t2 = self.index_mtime[page]
					if isinstance(t1, time.struct_time):
						t1 = calendar.timegm(t1)
					if isinstance(t2, time.struct_time):
						t2 = calendar.timegm(t2)
					t1, t2 = int(t1), int(t2)
					return t1 == t2
				else:
					# base relay does not provide modification times;
					# False would make the client load the index at every getIndexChanges call;
					# True would disable missing file management
					return True
			else:
				self.logger.debug("missing index for page '%s'; clearing local cache", page)
				del self.index[page]
				del self.index_mtime[page]
				return False
		else:
			return False

	def acquirePageLock(self, page, mode):
		blocking = self.lock_args.get('blocking', 5)
		has_lock = self.locked.get(page, False)
		if has_lock and not self.base_relay.hasLock(page):
			self.logger.warning("missing lock for page '%s'", page)
			has_lock = False
		if not has_lock:
			has_lock = self.base_relay.acquireLock(page, mode, **self.lock_args)
		if has_lock:
			#if not self.transaction_timestamp:
			# no need for reentrant locks
			self.transaction_timestamp = int(round(time.time()))
			self.locked[page] = True
		else:
			raise PostponeRequest
		return has_lock

	def releasePageLock(self, page):
		#self.base_relay.releaseLock(page)
		# we need that base_relay.releaseLock uses self.unlink instead of base_relay.unlink
		self.unlink(self.base_relay.lock(page))
		self.locked[page] = False
		self.transaction_timestamp = None

	def tryAcquirePageLock(self, page, mode):
		"""
		Non-blocking equivalent of `acquirePageLock`.
		"""
		has_lock = self.locked.get(page, False)
		if has_lock and not self.base_relay.hasLock(page):
			self.logger.warning("missing lock for page '%s'", page)
			has_lock = False
		if not has_lock:
			lock_args = dict(self.lock_args)
			lock_args['blocking'] = False
			try:
				has_lock = self.base_relay.acquireLock(page, mode, **lock_args)
			except ExpressInterrupt:
				raise
			except Exception as e:
				self.logger.debug("failed to acquire lock: %s", e)
				has_lock = False
		if has_lock:
			#if not self.transaction_timestamp:
			# no need for reentrant locks
			self.transaction_timestamp = int(round(time.time()))
			self.locked[page] = True
		return has_lock

	def unlink(self, remote_file):
		if not remote_file:
			raise ValueError
		#if self.base_relay.exists(remote_file):
		try:
			self.base_relay.unlink(remote_file)
		except ExpressInterrupt:
			raise
		except Exception as e:
			self.logger.debug("cannot delete file '%s': %s", remote_file, e)
		self.listing_cache = [ (l,s) for l,s in self.listing_cache if l != remote_file ]

	def setUpdateData(self, page, datafile):
		self.base_relay._push(datafile, self.updateData(page, mode='w'))

	def _force(self, operation, target, func, *args, **kwargs):
		while True:
			try:
				return func(*args, **kwargs)
			except ExpressInterrupt:
				raise
			except Exception as exc:
				self.logger.warning("failed to %s '%s.%d'", operation, target, self.transaction_timestamp)
				self.logger.debug("%s", exc)
				self.logger.debug(traceback.format_exc())
				raise # for debugging
			else:
				break

	def sanityChecks(self, page):
		if not self.base_relay.hasLock(page):
			msg = "missing lock for page '{}'".format(page)
			self.logger.warning(msg)
			raise RuntimeError(msg)
		self.refreshListing()
		while True:
			update_index = self.updateIndex(page, mode='r')
			if update_index:
				#assert not self.base_relay.exists(self.updateData(page))
				self.logger.debug("clearing update index '{}'".format(update_index))
				self.unlink(update_index)
			else:
				break

	def storageSpace(self):
		used, quota = self.base_relay.storageSpace()
		#if used is None:
		#	used = 0
		#for size in self.archive_size.values():
		#	if size:
		#		used += float(size) / 1048576 # in MB
		return used, quota

	def allPages(self):
		return [ self.page('a') ]

	def listPages(self, remote_dir=''):
		self.refreshListing(remote_dir)
		files = []
		for filename, _ in self.listing_cache:
			if self._persistent_index_prefix:
				if filename.startswith(self._persistent_index_prefix):
					filename = filename[len(self._persistent_index_prefix):]
				else:
					continue
			if self._persistent_index_suffix:
				if filename.endswith(self._persistent_index_suffix):
					filename = filename[:-len(self._persistent_index_suffix)]
				else:
					continue
			if filename and '.' not in filename:
				files.append(filename)
		return files

	def listReady(self, remote_dir='', recursive=True):
		return self.base_relay.listReady(remote_dir, recursive)

	def listCorrupted(self, remote_dir='', recursive=True):
		return self.skipIndexRelated(self.base_relay.listCorrupted(remote_dir, recursive))
		#return self.base_relay.listCorrupted(remote_dir, recursive=False)

	def listTransferred(self, remote_dir='', end2end=True, recursive=True):
		return self.skipIndexRelated(self.base_relay.listTransferred(remote_dir, end2end, recursive))

	def skipIndexRelated(self, files_or_locks):
		if not self._persistent_index_prefix.startswith('.') or \
			not self._update_index_prefix.startswith('.') or \
			not self._update_data_prefix.startswith('.'):
			raise NotImplementedError
		return files_or_locks

	def open(self):
		self.base_relay.open()

	def close(self):
		self.base_relay.close()

	def hasLock(self, page):
		return self.base_relay.hasLock(page)

	def updateRelated(self, page, filename):
		# this may have never been tested
		filename = os.path.basename(filename)
		prefix = self._persistent_index_prefix + page
		suffix = self._persistent_index_suffix
		may_be_global_index = filename.startswith(prefix) and (not suffix or filename.endswith(suffix))
		prefixes = [self._update_index_prefix, self._update_data_prefix]
		suffixes = [self._update_index_suffix, self._update_data_suffix]
		timestamps = [self._timestamp_index, self._timestamp_data]
		for prefix, suffix, timestamp in zip(prefixes, suffixes, timestamps):
			prefix += page
			if filename.startswith(prefix) and (not suffix or filename.endswith(suffix)):
				if timestamp:
					filename = filename[len(prefix):]
					if suffix:
						filename = filename[:-len(suffix)]
					if filename.startswith('.'):
						return True
					else:
						continue
				elif may_be_global_index:
					raise ValueError("cannot differentiate between global and update indices: '%s'", filename)
				else:
					return True
		return False

	def repairUpdates(self):
		self.refreshListing()
		for page in self.allPages():
			if self.base_relay.lock(page) in [ l for l,_ in self.listing_cache ]:
				lock = self.base_relay.getLockInfo(page)
				if not lock or not lock.owner or lock.owner == self.client:
					if not lock or not lock.mode or lock.mode == 'w':
						for f,_ in self.listing_cache:
							if self.updateRelated(page, f):
								self.logger.debug("releasing remnant update file '%s'", f)
								self.unlink(f)
					self.logger.debug("releasing remnant lock for page '%s'", page)
					self.releasePageLock(page)

	def requestMissing(self, page, remote_files):
		if not remote_files:
			return
		# lock is acquired
		remote_index = self.persistentIndex(page)
		tmp = self.base_relay.newTemporaryFile()
		try:
			self.base_relay._get(remote_index, tmp)
			self.index[page], _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
			ok = False
			for remote_file in remote_files:
				try:
					del self.index[page][remote_file]
				except KeyError:
					self.logger.debug("missing file '%s' not in index", remote_file)
				else:
					ok = True
					self.logger.info("file '%s' reported missing", remote_file)
			if not ok:
				return
			if self.index[page]:
				write_index(tmp, self.index[page], groupby=self.metadata_group_by, compress=True)
				self.logger.debug("updating index for page '%s'", page)
				self.base_relay._push(tmp, remote_index)
				self.remoteListing()
				self.index_mtime[page] = [ mtime for name, mtime in self.listing_cache if name == remote_index ][0]
			else:
				self.unlink(remote_index)
		finally:
			self.base_relay.delTemporaryFile(tmp)


	def getIndexChanges(self, page, sync=True, check_mtime=False):
		index = {}
		location = self.persistentIndex(page)
		index_mtime = [ mtime for name, mtime in self.listing_cache if name == location ]
		if index_mtime:
			index_mtime = index_mtime[0]
			timestamp = self.updateTimestamp(page, mode='r') # read last update timestamp on the relay
			if self.loaded(page, index_mtime, check_mtime):
				if not timestamp:
					return index
				if page not in self.last_update or self.last_update[page] < timestamp:
					location = self.updateIndex(page, mode='r')
					self.logger.debug("downloading index update '%s' for page '%s'", timestamp, page)
					tmp = self.base_relay.newTemporaryFile()
					self.base_relay._get(location, tmp)
					index, pullers = read_index(tmp)
					self.last_update_cache[page] = (index, pullers)
					if sync:
						for resource, mdata in index.items():
							self.index[page][resource] = mdata
					self.base_relay.delTemporaryFile(tmp)
				elif self.last_update[page] == timestamp:
					# updates are not always consumed at the first getUpdate call;
					# setUpdate will not call getUpdateIndex and will ignore the value below
					try:
						index, _ = self.last_update_cache[page]
					except KeyError:
						pass
			else:
				self.logger.debug("downloading index for page '%s'", page)
				tmp = self.base_relay.newTemporaryFile()
				self.base_relay._get(location, tmp)
				index, _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
				self.index[page] = index
				self.index_mtime[page] = index_mtime
				self.base_relay.delTemporaryFile(tmp)
			if timestamp:
				self.last_update[page] = timestamp
		return index

	def getPageIndex(self, page):
		self.getIndexChanges(page, sync=True, check_mtime=True)
		return self.index.get(page, {})

	def getUpdateIndex(self, page, sync=True):
		return self.getIndexChanges(page, sync, check_mtime=False)

	def getUpdateData(self, page, destination):
		self.base_relay._get(self.updateData(page, mode='r'), destination)

	def setPageIndex(self, page, index):
		index_location = self.persistentIndex(page)
		if not index:
			self.logger.debug("removing empty index for page '%s'", page)
			self.base_relay.unlink(index_location)
			return
		self.logger.debug("uploading index for page '%s'", page)
		fd, tmp = tempfile.mkstemp()
		try:
			os.close(fd)
			write_index(tmp, index, groupby=self.metadata_group_by, compress=True)
			self._force('update page index', page, self.base_relay._push, tmp, index_location)
		finally:
			os.unlink(tmp)

	def setUpdateIndex(self, page, index, sync=True):
		if not index:
			self.logger.warning("empty update index for page '%s'", page)
			return
		index_location = self.persistentIndex(page)
		exists = index_location in [ f for f,_ in self.listing_cache ]
		tmp = self.base_relay.newTemporaryFile()
		index_update = index
		upload_index = sync or not exists
		if upload_index:
			if exists:
				if page not in self.index or not self.index[page]:
					raise RuntimeError("page '%s' exists but is empty", page)
				index = self.index[page]
				index.update(index_update)
			if sync:
				self.index[page] = index
			#
			self.logger.debug("uploading index for page '%s'", page)
			write_index(tmp, index, groupby=self.metadata_group_by, compress=True)
			self._force('update page index', page, self.base_relay._push, tmp, index_location)
		#
		if True:#exists:
			write_index(tmp, index_update)
			update_location = self.updateIndex(page, mode='w')
			if self._timestamp_index:
				self.logger.debug("uploading index update '%s' for page '%s'",
						self.updateTimestamp(page, mode='w'), page)
			self._force('push update index', page, self.base_relay._push, tmp, update_location)
		self.base_relay.delTemporaryFile(tmp)
		#
		self.remoteListing()
		if upload_index:
			self.index_mtime[page] = [ mtime for name, mtime in self.listing_cache if name == index_location ][0]

	def setUpdateData(self, page, data):
		self.base_relay._push(data, self.updateData(page, mode='w'))

	def consumeUpdate(self, page, terminate=None):
		try:
			index, pullers = self.last_update_cache[page]
		except KeyError:
			index = {}
			pullers = []
		pullers.append(self.client)
		location = self.updateIndex(page, mode='r')
		if terminate and terminate(pullers):
			if location:
				self.unlink(location)
			location = self.updateData(page, mode='r')
			if location:
				self.unlink(location)
			return
		#
		#if not location:
		#	# no update yet on the relay
		#	self.transaction_timestamp = None
		#	location = self.updateIndex(page, mode='w')
		#
		tmp = self.base_relay.newTemporaryFile()
		write_index(tmp, index, pullers)
		self.logger.debug("uploading index update for page '%s'", page)
		self._force('push update index', page, self.base_relay._push, tmp, location)
		self.base_relay.delTemporaryFile(tmp)

	def indexed(self, remote_file):
		return True

	def repair(self, *args, **kwargs):
		self.base_relay.repair(*args, **kwargs)

	def getMetadata(self, remote_file, *args, **kwargs):
		if self.indexed(remote_file):
			try:
				return parse_metadata(self.index[self.page(remote_file)][remote_file])
			except KeyError:
				self.logger.warning("missing file '%s' in index page '%s'", remote_file, self.page(remote_file))
				raise
		else:
			return self.base_relay.getMetadata(remote_file, *args, **kwargs)

	def hasUpdate(self, page):
		self.remoteListing()
		return self.updateTimestamp(page, mode='r') is not None



class TopDirectoriesIndex(IndexRelay):
	def __init__(self, *args, **kwargs): 
		self.nlevels = kwargs.pop('nlevels', 1)
		IndexRelay.__init__(self, *args, **kwargs)

	def page(self, resource):
		levels = []
		dirname = os.path.dirname(resource)
		while dirname:
			dirname, level = os.path.split(dirname)
			levels.append(level)
		levels = levels[-1:-1-self.nlevels:-1]
		if len(levels) == self.nlevels:
			return '_'.join(levels).replace('.', '_')
		else:
			return IndexRelay.page(self, resource)

	def allPages(self):
		self.refreshListing()
		locks_and_indices = self.listPages()
		for entry, _ in self.listing_cache:
			if self.base_relay._isLock(entry):
				page = self.base_relay._fromLock(entry)
				if page not in [ l for l, _ in self.listing_cache ]:
					locks_and_indices.append(page)
		return set(IndexRelay.allPages(self) + locks_and_indices)

