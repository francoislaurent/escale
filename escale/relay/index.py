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
from collections import defaultdict, MutableMapping


class AbstractIndexRelay(AbstractRelay):

	def reloadIndex(self):
		raise NotImplementedError('abstract method')

	def listPages(self):
		raise NotImplementedError('abstract method')

	def getPageIndex(self, page):
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

	def consumeUpdate(self, page, **kwargs):
		raise NotImplementedError('abstract method')

	#def requestMissing(self, remote_file):
	#	raise NotImplementedError('abstract method')

	def repairUpdates(self):
		raise NotImplementedError('abstract method')

	def acquirePageLock(self, page):
		raise NotImplementedError('abstract method')

	def releasePageLock(self, page):
		raise NotImplementedError('abstract method')


class IndexUpdate(MutableMapping):

	def __init__(self, relay, page):
		self.relay = relay
		self.page = page
		self.content = {}

	def __enter__(self):
		if not self.relay.acquirePageLock(self.page):
			raise PostponeRequest("failed to lock page '%s'", self.page)

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
		self.relay.releasePageLock(self.page)

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
		IndexUpdate.__init__(self, relay, page)
		self.terminate = terminate

	def __enter__(self):
		IndexUpdate.__enter__(self)
		self.content = self.relay.getUpdateIndex(self.page)

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
		self.relay.consumeUpdate(self.page, self.terminate)
		IndexUpdate.__exit__(self, exc_type, *args)


class UpdateWrite(IndexUpdate):

	def __exit__(self, exc_type, *args):
		if exc_type is not None:
			return
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
		lock_args = kwargs.pop('lock_args', {})
		self.base_relay = base(*args, **kwargs)
		self.lock_args = lock_args
		self.fresh = True
		self.locked = {}
		self.missing_files = {}
		self.transaction_timestamp = None
		self.index = {}
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
		if mode is None:
			mode = self.mode
		if self._timestamp_index:
			ts = self.updateTimestamp(page, mode=mode)
			if ts:
				ts = '.{}'.format(ts)
			else:
				return None
		else:
			ts = ''
		return '{}{}{}{}'.format(self._update_index_prefix, page, ts, self._update_index_suffix)

	def updateData(self, page):
		if self._timestamp_data:
			ts = '.{}'.format(self.transaction_timestamp)
		else:
			ts = ''
		return '{}{}{}{}'.format(self._update_data_prefix, page, ts, self._update_data_suffix)

	def updateTimestamp(self, page, mode=None):
		#if mode is None:
		#	mode = self.mode
		#if mode == 'r':
		#	self.refreshListing() # page should be locked
		timestamp = None
		if self._timestamp_index:
			if mode == 'w':
				if not self.transaction_timestamp:
					self.transaction_timestamp = int(round(time.time()))
				timestamp = self.transaction_timestamp
			elif mode is None or mode == 'r':
				ls = self.listing_cache # should be up-to-date
				prefix = '{}{}.'.format(self._update_index_prefix, page)
				ls = [ l[len(prefix):] for l, _ in ls if l.startswith(prefix) ]
				if self._update_index_suffix:
					suffix_len = len(self._update_index_suffix)
					ls = [ l[:-suffix_len] for l in ls if l.endswith(self._update_index_suffix) ]
				ts = []
				for l in ls:
					try:
						ts.append(int(l))
					except ValueError:
						pass
				if ts:
					if ts[1:]:
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

	def reloadIndex(self):
		for page in self.listPages():
			if not self.acquirePageLock(page):
				self.logger.warning("cannot lock page '%s'", page)
				continue
			tmp = self.base_relay.newTemporaryFile()
			try:
				self.base_relay._get(self.persistentIndex(page), tmp)
				self.index[page], _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
			finally:
				self.base_relay.delTemporaryFile(tmp)
				self.releasePageLock(page)
		self.fresh = True

	def _getPersistentIndex(self, page, mode=None, locked=False):
		if mode is None:
			mode = self.mode
		location = self.persistentIndex(page)
		if location in [ filename for filename, _ in self.listing_cache ]:#self.base_relay.exists(location):
			release_lock = False
			timestamp = self.updateTimestamp(page, mode)
			if page in self.index:
				if mode == 'w' or not timestamp:
					return
				if page not in self.last_update or self.last_update[page] < timestamp:
					location = self.updateIndex(page, mode)
					if not locked:
						if self.acquirePageLock(page, mode=mode):
							release_lock = False # do not release lock now!!
						else:
							self.logger.debug("failed to lock page '%s'", page)
							return
					self.logger.info("downloading index update '%s' for page '%s'", timestamp, page)
					tmp = self.base_relay.newTemporaryFile()
					self.base_relay._get(location, tmp)
					metadata, pullers = read_index(tmp)
					self.last_update_cache[page] = (metadata, pullers)
					for resource, mdata in metadata.items():
						self.index[page][resource] = mdata
					self.base_relay.delTemporaryFile(tmp)
			else:
				if not locked:
					if self.acquirePageLock(page, mode=mode):
						release_lock = True
					else:
						self.logger.debug("failed to lock page '%s'", page)
						return
				self.logger.info("downloading index for page '%s'", page)
				tmp = self.base_relay.newTemporaryFile()
				self.base_relay._get(location, tmp)
				metadata, _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
				self.index[page] = metadata
				self.base_relay.delTemporaryFile(tmp)
			if timestamp:
				self.last_update[page] = timestamp
			if release_lock:
				try:
					self.releasePageLock(page)
				except ExpressInterrupt:
					raise
				except:
					# handle missing lock exceptions that happen on test platforms
					# with multiple clients supposed to run on different machines
					pass

	def _setIndices(self, page):
		assert page in self.locked_pages # already locked
		assert not self.mode or self.mode != 'r'
		location = self.persistentIndex(page)
		exists = self.base_relay.exists(location)
		if page not in self.index:
			msg = "no local index for page '{}'".format(page)
			self.logger.warning(msg)
			raise RuntimeError(msg)
		tmp = self.base_relay.newTemporaryFile()
		metadata = self.index[page]
		self.logger.info("uploading index for page '%s'", page)
		write_index(tmp, metadata, groupby=self.metadata_group_by, compress=True)
		self._force('update page index', page, self.base_relay._push, tmp, location)
		if exists:
			write_index(tmp, self.locked_pages[page])
			location = self.updateIndex(page, mode='w')
			if self._timestamp_index:
				self.logger.info("uploading index update '%s' for page '%s'",
						self.updateTimestamp(page, mode='w'), page)
			self._force('push update index', page, self.base_relay._push, tmp, location)
		self.base_relay.delTemporaryFile(tmp)

	def _getMetadata(self, remote_file, output_file=None, timestamp_format=None):
		page = self.page(remote_file)
		self.getPersistentIndex(page)
		metadata = self.index[page].get(remote_file, None)
		if metadata:
			if output_file:
				with open(output_file, 'w') as f:
					f.write(metadata)
				return output_file
			else:
				return parse_metadata(metadata, target=remote_file, \
					log=self.logger.debug, timestamp_format=timestamp_format)
		else:
			if self.mode == 'r':
				msg = "missing record '{}' in page '{}'".format(remote_file, page)
				self.logger.critical(msg)
				raise RuntimeError(msg)
			return None

	def acquirePageLock(self, page):
		blocking = self.lock_args.get('blocking', 5)
		has_lock = self.locked.get(page, False)
		if not has_lock:
			has_lock = self.base_relay.acquireLock(page, **self.lock_args)
		if has_lock:
			if not self.transaction_timestamp:
				self.transaction_timestamp = int(round(time.time()))
			self.locked[page] = True
		else:
			raise PostponeRequest
		return has_lock

	def releasePageLock(self, page):
		self.base_relay.releaseLock(page)
		self.locked[page] = False

	def _setMetadata(self, remote_file, last_modified=None, checksum=None):
		page = self.page(remote_file)
		if last_modified:
			metadata = repr(Metadata(pusher=self.client, target=remote_file,
					timestamp=last_modified, checksum=checksum))
		else:
			metadata = None
		if page not in self.index:
			self.getPersistentIndex(page, mode='w')
			self.index[page] = {}
		self.index[page][remote_file] = metadata
		assert page in self.locked_pages
		assert remote_file in self.locked_pages[page]
		self.locked_pages[page][remote_file] = metadata

	def _push(self, local_file, remote_dest, last_modified=None, checksum=None, blocking=True):
		"""
		Send local file to the relay repository.

		Files are added to a local archive.

		Once the uncompressed archive reaches `max_page_size`, it is compressed, encrypted and sent
		to the relay.
		See also :meth:`checkSize`.
		"""
		self.mode = 'w'
		page = self.page(remote_dest)
		if self.updateData(page) in [ f for f, _ in self.listing_cache ]:
			raise PostponeRequest
			return False
		if not self.acquirePageLock(page, resource=remote_dest, blocking=blocking):
			return False
		self.setMetadata(remote_dest, last_modified=last_modified, checksum=checksum)
		self.addToArchive(page, local_file, remote_dest)
		self.checkSize(page)
		return True

	def unlink(self, remote_file):
		if self.base_relay.exists(remote_file):
			self.base_relay.unlink(remote_file)
		self.listing_cache = [ (l,s) for l,s in self.listing_cache if l != remote_file ]

	def _localCopy(self, remote_file, page=None):
		if not page:
			page = self.page(remote_file)
		if self.archive.get(page, None):
			local_file = join(self.archive[page], remote_file)
			if os.path.exists(local_file):
				return local_file
		return None

	def _isAvailable(self, remote_file, page=None):
		return self.localCopy(remote_file, page) is not None

	def _pop(self, remote_file, local_dest, placeholder=True, blocking=True, refresh_index=True,
		**kwargs):
		"""
		Get a file from the relay repository.

		The desired file should be available in the current update on the relay.

		The archive is downloaded once, and then other files in the same archive are locally moved
		from the local copy of the archive to the local repository.
		"""
		self.mode = 'r'
		page = self.page(remote_file)
		if not self.isAvailable(remote_file, page):
			if not self.base_relay.exists(self.updateData(page)):
				self.request(page, remote_file, local_dest)
				return False
			if not self.acquirePageLock(page, resource=remote_file, blocking=blocking):
				return False
			if refresh_index:
				self.getPersistentIndex(page, mode='r', locked=True)
			if placeholder:
				index, pullers = self.last_update_cache.get(page, ({}, []))
				let = len(pullers) < placeholder - 1
			else:
				let = False
			tmp = self.base_relay.newTemporaryFile()
			if self.encryption:
				_tmp = tmp
				tmp = self.encryption.prepare(page)
			if let:
				self.base_relay._get(page, tmp)
			else:
				self.base_relay._pop(page, tmp)
			if self.encryption:
				self.encryption.decrypt(tmp, _tmp)
				tmp = _tmp
			#if self.archive.get(page, None):
			#	msg = "existing archive for page '{}'".format(page)
			#	self.logger.debug(msg)
			#	shutil.rmtree(self.archive[page])
			if page not in self.archive:
				self.archive[page] = tempfile.mkdtemp()
				self.archive_size[page] = None # in read mode, does not matter
			with tarfile.open(tmp, mode='r:bz2') as tar:
				tar.extractall(self.archive[page])
			if placeholder:
				update_index = self.updateIndex(page, mode='r')
				if let:
					# mark update index as read
					pullers.append(self.client)
					write_index(tmp, index, pullers)
					self.base_relay._push(tmp, update_index)
				elif update_index in [ l for l, _ in self.listing_cache ]:
					# delete update index
					try:
						self.unlink(update_index)
					except ExpressInterrupt:
						raise
					except Exception as exc:
						self.logger.warning("failed to delete update index for page '%s'", page)
						self.logger.info("%s", exc) # debug
						self.logger.info(traceback.format_exc())
			self.base_relay.delTemporaryFile(tmp)
			if not self.isAvailable(remote_file, page):
				self.request(page, remote_file, local_dest)
			self.releasePageLock(page)
			if not let:
				self.refreshListing(force=True)
		dirname = os.path.dirname(local_dest)
		if dirname and not os.path.isdir(dirname):
			os.makedirs(dirname)
		new_file = self.localCopy(remote_file, page)
		if new_file:
			shutil.move(new_file, local_dest)
			return True
		else:
			self.logger.warning("missing '%s' file", remote_file)
			return False

	def _delete(self, remote_file):
		# force update deletion;
		# flagging the full update as duplicate is a valid strategy as long as 
		# files were transferred by the same update
		local_file = self.localCopy(remote_file)
		if local_file:
			os.unlink(local_file)
			# TODO: check the update data file has been removed from the relay
			pass
		else:
			# pop with placeholder=1 so that the update data is removed from the relay
			tmp = self.base_relay.newTemporaryFile()
			self.pop(remote_file, tmp, placeholder=1, refresh_index=False)
			self.base_relay.delTemporaryFile(tmp)

	def _addToArchive(self, page, local_file, remote_dest):
		if not self.archive.get(page, None):
			self.archive[page] = tempfile.mkdtemp()
			self.archive_size[page] = 0
		dirname = os.path.dirname(remote_dest)
		if dirname:
			dirname = os.path.join(self.archive[page], dirname)
			if not os.path.exists(dirname):
				os.makedirs(dirname)
		copyfile(local_file, os.path.join(self.archive[page], remote_dest))
		self.archive_size[page] += os.stat(local_file).st_size # without compression

	def setUpdateData(self, page, datafile):
		self.base_relay._push(datafile, self.updateData(page))

	def _setUpdateData(self, page):
		if not self.archive.get(page, None):
			msg = "page '{}' is corrupted".format(page)
			self.logger.error(msg)
			raise RuntimeError(msg)
		tmp = self.base_relay.newTemporaryFile()
		empty = True
		with tarfile.open(tmp, mode='w:bz2') as tar:
			for member in os.listdir(self.archive[page]):
				empty = False
				tar.add(join(self.archive[page], member), arcname=member,
					recursive=True)
		if empty:
			msg = "empty archive '{}'".format(self.archive.get(page, None))
			self.logger.critical(msg)
			raise RuntimeError(msg)
		if self.encryption:
			_tmp = tmp
			tmp = self.encryption.encrypt(_tmp)
		self.base_relay._push(tmp, self.updateData(page))
		if self.encryption:
			self.encryption.finalize(tmp)
			tmp = _tmp
		self.base_relay.delTemporaryFile(tmp)
		shutil.rmtree(self.archive[page])
		self.archive[page] = None
		self.archive_size[page] = 0

	def _force(self, operation, target, func, *args, **kwargs):
		while True:
			try:
				return func(*args, **kwargs)
			except ExpressInterrupt:
				raise
			except Exception as exc:
				self.logger.info("failed to %s '%s.%d'", operation, target, self.transaction_timestamp)
				self.logger.debug("%s", exc)
				self.logger.debug(traceback.format_exc())
				raise # for debugging
			else:
				break

	def _commit(self):
		if any([ files is None for files in self.locked_pages.values() ]):
			# recover after failure
			# TODO: debug if this case ever happen
			msg = 'any([ files is None for files in self.locked_pages.values() ])'
			self.logger.critical(msg)
			raise NotImplementedError(msg)
		force_refresh = False
		for page in list(self.locked_pages.keys()):
			if self.locked_pages[page] is None:
				self.logger.warning("releasing page '%s'", page)
			else:
				self.sanityChecks(page)
				self.logger.info("committing page '%s'", page)
				self.setUpdateData(page)
				self.setIndices(page)
				force_refresh = True
			if self.base_relay.hasLock(page):
				try:
					self.releasePageLock(page)
				except ExpressInterrupt:
					raise
				except Exception as exc:
					self.logger.warning("failed to release lock for page '%s'", page)
					self.logger.info("%s", exc) # debug
					self.logger.info(traceback.format_exc())
			else:
				self.logger.warning("no lock for page '%s'", page)
			self.archive[page] = None
			self.archive_size[page] = 0
		self.locked_pages = {}
		self.transaction_timestamp = None
		if force_refresh:
			self.refreshListing(force=True)

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
	#	ready = []
	#	tmp = None
	#	for page in self.listPages(remote_dir):
	#		if not (self.fresh or self.updateData(page) in [ f for f, _ in self.listing_cache ]):
	#			# if no update data are available, skip page
	#			continue
	#		self.getPersistentIndex(page, mode='r')
	#		self.fresh = False
	#		update_index = self.updateIndex(page, mode='r')
	#		if update_index and self.base_relay.exists(update_index):
	#			if tmp is None:
	#				tmp = self.base_relay.newTemporaryFile()
	#			try:
	#				self.base_relay._get(update_index, tmp)
	#			except ExpressInterrupt:
	#				raise
	#			except Exception as exc:
	#				self.logger.warning("failed to retrieve update index for page '%s'", page)
	#				self.logger.debug(exc)
	#				self.logger.debug(traceback.format_exc())
	#				raise # for debugging
	#			else:
	#				files, _ = read_index(tmp)
	#				ready.append(files.keys())
	#		else:
	#			ready.append(self.index[page].keys())
	#	if tmp:
	#		self.base_relay.delTemporaryFile(tmp)
	#	if ready:
	#		return list(itertools.chain(*ready))
	#	else:
	#		return []

	def listCorrupted(self, remote_dir='', recursive=True):
		return self.skipIndexRelated(self.base_relay.listCorrupted(remote_dir, recursive))
		#return self.base_relay.listCorrupted(remote_dir, recursive=False)

	def listTransferred(self, remote_dir='', end2end=True, recursive=True):
		return self.skipIndexRelated(self.base_relay.listTransferred(remote_dir, end2end, recursive))
		## this runs at the beginning of manager.upload;
		## clear update caches if manager.download was called
		##for page in self.archive:
		##	if self.archive[page] and os.path.exists(self.archive[page]):
		##		shutil.rmtree(self.archive[page])
		##
		#files = []
		#for page in self.listPages(remote_dir):
		#	self.getPersistentIndex(page, mode='w')
		#	all_files = self.index[page].keys()
		#	if end2end:
		#		raise NotImplementedError
		#	else:
		#		files.append(all_files)
		#if files:
		#	return list(itertools.chain(*files))
		#else:
		#	return []

	def skipIndexRelated(self, ls):
		if not self._persistent_index_prefix.startswith('.') or \
			not self._update_index_prefix.startswith('.') or \
			not self._update_data_prefix.startswith('.'):
			raise NotImplementedError
		return ls

	def open(self):
		self.base_relay.open()

	def close(self):
		#for page in self.archive:
		#	if self.archive[page] and os.path.exists(self.archive[page]):
		#		shutil.rmtree(self.archive[page])
		self.base_relay.close()

	def repairUpdates(self):
		for page in self.listPages():
			if self.lock(page) in [ l for l,_ in self.listing_cache ]:
				lock = self.base_relay.getLockInfo(page)
				if not lock or not lock.owner or lock.owner == self.client:
					if not lock or not lock.mode or lock.mode == 'w':
						files = []
						for f,_ in self.listing_cache:
							if f.startswith(self._update_index_prefix+page) and \
								(not self._update_index_suffix or f.endswith(self._update_index_suffix)):
								files.append(f)
							elif f.startswith(self._update_data_prefix+page) and \
								(not self._update_data_suffix or f.endswith(self._update_data_suffix)):
								files.append(f)
						for f in files:
							self.unlink(f)
					self.base_relay.releaseLock(page)

	def request(self, page, remote_file, local_dest=None):
		if page in self.archive:
			msg = "missing file '{}' in archive '{}'".format(remote_file, self.archive[page])
			self.logger.debug(msg)
			if local_dest and os.path.isfile(local_dest):
				msg = "the missing file exists in the local repository; this may be a runtime error"
				self.logger.debug(msg)
		self.logger.info("file '%s' reported missing", remote_file)
		missing_files = self.missing_files.get(page, [])
		missing_files.append(remote_file)
		self.missing_files[page] = missing_files


	def getIndexChanges(self, page, sync=True):
		location = self.persistentIndex(page)
		if location in [ filename for filename, _ in self.listing_cache ]:#self.base_relay.exists(location):
			timestamp = self.updateTimestamp(page, mode='r') # read last update timestamp on the relay
			if page in self.index:
				if page not in self.last_update or self.last_update[page] < timestamp:
					self.getUpdateIndex(page)
					location = self.updateIndex(page, mode)
					self.logger.info("downloading index update '%s' for page '%s'", timestamp, page)
					tmp = self.base_relay.newTemporaryFile()
					self.base_relay._get(location, tmp)
					index, pullers = read_index(tmp)
					self.last_update_cache[page] = (index, pullers)
					if sync:
						for resource, mdata in index.items():
							self.index[page][resource] = mdata
					self.base_relay.delTemporaryFile(tmp)
			else:
				self.logger.info("downloading index for page '%s'", page)
				tmp = self.base_relay.newTemporaryFile()
				self.base_relay._get(location, tmp)
				index, _ = read_index(tmp, groupby=self.metadata_group_by, compress=True)
				self.index[page] = index
				self.base_relay.delTemporaryFile(tmp)
			if timestamp:
				self.last_update[page] = timestamp
		else:
			index = {}
		return index

	def getPageIndex(self, page):
		self.getIndexChanges(page, True)
		return self.index.get(page, {})

	def getUpdateIndex(self, page, sync=True):
		return self.getIndexChanges(page, sync)

	def getUpdateData(self, page, destination):
		self.base_relay._get(self.updateData(page), destination)

	def setUpdateIndex(self, page, index, sync=True):
		if not index:
			self.logger.warning("empty update index for page '%s'", page)
			return
		location = self.persistentIndex(page)
		exists = location in [ f for f,_ in self.listing_cache ]
		tmp = self.base_relay.newTemporaryFile()
		index_update = index
		if sync or not exists:
			if exists:
				if page not in self.index or not self.index[page]:
					raise RuntimeError("page '%s' exists but is empty", page)
				index = self.index[page]
				index.update(index_update)
			if sync:
				self.index[page] = index
			#
			self.logger.info("uploading index for page '%s'", page)
			write_index(tmp, index, groupby=self.metadata_group_by, compress=True)
			self._force('update page index', page, self.base_relay._push, tmp, location)
		#
		if exists:
			write_index(tmp, index_update)
			location = self.updateIndex(page, mode='w')
			if self._timestamp_index:
				self.logger.info("uploading index update '%s' for page '%s'",
						self.updateTimestamp(page, mode='w'), page)
			self._force('push update index', page, self.base_relay._push, tmp, location)
		self.base_relay.delTemporaryFile(tmp)

	def setUpdateData(self, page, data):
		self.base_relay._push(data, self.updateData(page))

	def consumeUpdate(self, page, terminate=None):
		try:
			index, pullers = self.last_update_cache[page]
		except KeyError:
			index = {}
			pullers = []
		pullers.append(self.client)
		location = self.updateIndex(page, mode='r')
		if terminate and terminate(pullers):
			self.unlink(location)
			self.unlink(self.updateData(page))
			return
		#
		if not location:
			# no update yet on the relay
			self.transaction_timestamp = None
			location = self.updateIndex(page, mode='w')
		#
		tmp = self.base_relay.newTemporaryFile()
		write_index(tmp, index, pullers)
		self.logger.info("uploading index update for page '%s'", page)
		self._force('push update index', page, self.base_relay._push, tmp, location)
		self.base_relay.delTemporaryFile(tmp)

	def indexed(self, remote_file):
		return True

	def repair(self, *args, **kwargs):
		self.base_relay.repair(*args, **kwargs)

