# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# Copyright © 2017, François Laurent
#      Contribution: documentation, update timestamp, encryption, listing cooldown

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


puller_breaker = '---pullers---'

def write_index(filename, metadata, pullers=[]):
	"""
	Write index to file.
	"""
	with open(filename, 'w') as f:
		for resource in metadata:
			mdata = metadata[resource]
			if mdata:
				if not mdata.endswith('\n'):
					mdata += '\n'
			else:
				mdata = '' # string
			nchars = len(mdata)
			f.write('{} {}\n{}'.format(resource, nchars, mdata))
		if pullers:
			f.write(puller_breaker)
			for reader in pullers:
				f.write('\n'+reader)

def read_index(filename):
	"""
	Read index from file.
	"""
	metadata = {}
	pullers = []
	with open(filename, 'r') as f:
		while True:
			line = f.readline().rstrip()
			has_pullers = line == puller_breaker
			if line and not has_pullers:
				resource, nchars = line.rsplit(None, 1)
				nchars = int(nchars)
				if nchars:
					metadata[resource] = f.read(nchars)
				else:
					metadata[resource] = None
			else:
				break
		if has_pullers:
			while line:
				line = f.readline()
				pullers.append(line.rstrip())
	return (metadata, pullers)



class RelayIndex(AbstractRelay):
	"""
	Index-based remote repository.

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
		mode = kwargs.get('mode', None) # mode is actually not passed to Relay
		config = kwargs.get('config', {})
		encryption = config.pop('encryption', None)
		max_page_size, max_page_size_unit = kwargs.pop('maxpagesize', (1024, None))
		try:
			mode = {'download': 'r', 'upload': 'w'}[mode]
		except KeyError:
			pass
		self.base_relay = base(*args, **kwargs)
		self.locked_pages = {}
		self.transaction_timestamp = None
		self.index = {}
		self.last_update = {}
		self.last_update_cache = {}
		self.mode = mode
		if max_page_size_unit:
			max_page_size = float(max_page_size) * storage_space_unit[max_page_size_unit]
		self.max_page_size = max_page_size
		self.encryption = encryption
		self.listing_time = None
		self.listing_cache = None
		self.listing_cooldown = 5
		self.archive = {}
		self.archive_size = {}
		self._persistent_index_prefix = '.'
		self._persistent_index_suffix = '.index'
		self._update_index_prefix = '.'
		self._update_index_suffix = '.update'
		self._timestamp_index = True
		self._update_data_prefix = ''
		self._update_data_suffix = ''
		self._timestamp_data = False

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
		if mode is None:
			mode = self.mode
		if mode == 'r':
			self.refreshListing()
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

	def refreshListing(self, remote_dir='', force=False):
		now = time.time()
		if force or not (self.listing_time and now - self.listing_time < self.listing_cooldown):
			self.listing_cache = list(self.base_relay._list(remote_dir, recursive=False, stats=('mtime',)))
			self.listing_time = now

	def getPersistentIndex(self, page, mode=None, locked=False):
		if mode is None:
			mode = self.mode
		location = self.persistentIndex(page)
		if location in [ filename for filename, _ in self.listing_cache ]:#self.base_relay.exists(location):
			timestamp = self.updateTimestamp(page, mode)
			if page in self.index:
				if mode == 'w' or not timestamp:
					return
				if page not in self.last_update or self.last_update[page] < timestamp:
					location = self.updateIndex(page, mode)
					tmp = self.base_relay.newTemporaryFile()
					self.logger.info("downloading index update '%s' for page '%s'", timestamp, page)
					self.base_relay._get(location, tmp)
					metadata, pullers = read_index(tmp)
					self.last_update_cache[page] = (metadata, pullers)
					for resource, mdata in metadata.items():
						self.index[page][resource] = mdata
					self.base_relay.delTemporaryFile(tmp)
			else:
				if not locked and not self.acquireLock(page, mode=mode, blocking=mode=='w'):
					return
				tmp = self.base_relay.newTemporaryFile()
				self.logger.info("downloading index for page '%s'", page)
				self.base_relay._get(location, tmp)
				if not locked:
					try:
						self.releaseLock(page)
					except ExpressInterrupt:
						raise
					except:
						# handle missing lock exceptions that happen on test platforms
						# with multiple clients supposed to run on different machines
						pass
				metadata, _ = read_index(tmp)
				self.index[page] = metadata
				self.base_relay.delTemporaryFile(tmp)
			self.last_update[page] = timestamp

	def setIndices(self, page):
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
		write_index(tmp, metadata)
		self._force('update page index', page, self.base_relay._push, tmp, location)
		if exists:
			write_index(tmp, self.locked_pages[page])
			location = self.updateIndex(page, mode='w')
			if self._timestamp_index:
				self.logger.info("uploading index update '%s' for page '%s'",
						self.updateTimestamp(page, mode='w'), page)
			self._force('push update index', page, self.base_relay._push, tmp, location)
		self.base_relay.delTemporaryFile(tmp)

	def getMetadata(self, remote_file, output_file=None, timestamp_format=None):
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

	def acquireLock(self, page=None, mode=None, resource=None, **kwargs):
		if not page and resource:
			page = self.page(resource)
		if not mode:
			mode = self.mode
		has_lock = page in self.locked_pages
		if not has_lock:
			kwargs['mode'] = mode
			has_lock = self.base_relay.acquireLock(page, **kwargs)
		if has_lock:
			locked_files = self.locked_pages.get(page, {})
			if not self.transaction_timestamp:
				self.transaction_timestamp = int(round(time.time()))
			if resource:
				locked_files[resource] = None # no metadata for now
			self.locked_pages[page] = locked_files
		elif self.locked_pages and mode == 'w':
			self.commit()
		else:
			raise PostponeRequest
		return has_lock

	def releaseLock(self, page):
		self.base_relay.releaseLock(page)
		del self.locked_pages[page]

	def setMetadata(self, remote_file, last_modified=None, checksum=None):
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

	def push(self, local_file, remote_dest, last_modified=None, checksum=None, blocking=True):
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
		if not self.acquireLock(page, resource=remote_dest, blocking=blocking):
			return False
		self.setMetadata(remote_dest, last_modified=last_modified, checksum=checksum)
		self.addToArchive(page, local_file, remote_dest)
		self.checkSize(page)
		return True

	def isAvailable(self, remote_file, page=None):
		if not page:
			page = self.page(remote_file)
		return self.archive.get(page, None) and os.path.exists(join(self.archive[page], remote_file))

	def pop(self, remote_file, local_dest, placeholder=True, blocking=True, **kwargs):
		"""
		Get a file from the relay repository.

		The desired file should be available in the current update on the relay.

		The archive is downloaded once, and then other files in the same archive are locally moved
		from the local copy of the archive to the local repository.
		"""
		self.mode = 'r'
		page = self.page(remote_file)
		if not self.isAvailable(remote_file, page):
			if not self.acquireLock(page, resource=remote_file, blocking=blocking):
				 return False
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
			if self.archive.get(page, None):
				msg = "existing archive for page '{}'".format(page)
				self.logger.debug(msg)
				shutil.rmtree(self.archive[page])
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
						self.base_relay.unlink(update_index)
					except ExpressInterrupt:
						raise
					except Exception as exc:
						self.logger.warning("failed to delete update index for page '%s'", page)
						self.logger.info("%s", exc) # debug
						self.logger.info(traceback.format_exc())
			self.base_relay.delTemporaryFile(tmp)
			if not self.isAvailable(remote_file, page):
				msg = "missing file '{}' in archive '{}'".format(remote_file, self.archive[page])
				self.logger.critical(msg)
				raise RuntimeError(msg)
			self.releaseLock(page)
		dirname = os.path.dirname(local_dest)
		if dirname and not os.path.isdir(dirname):
			os.makedirs(dirname)
		copyfile(join(self.archive[page], remote_file), local_dest)
		return True

	def addToArchive(self, page, local_file, remote_dest):
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

	def setUpdateData(self, page):
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

	def commit(self):
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
				self.logger.info("committing page '%s'", page)
				self.setUpdateData(page)
				self.setIndices(page)
				force_refresh = True
			if self.base_relay.hasLock(page):
				try:
					self.releaseLock(page)
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

	def checkSize(self, page):
		size = self.archive_size.get(page, None)
		if size:
			size = float(size) / 1048576 # in MB
			if self.max_page_size < size:
				self.commit()

	def storageSpace(self):
		used, quota = self.base_relay.storageSpace()
		if used is None:
			used = 0
		for size in self.archive_size.values():
			if size:
				used += float(size) / 1048576 # in MB
		return used, quota

	def remoteListing(self):
		if self.index and self.mode == 'w':
			self.commit()

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
			files.append(filename)
		return files

	def listReady(self, remote_dir='', recursive=True):
		ready = []
		tmp = self.base_relay.newTemporaryFile()
		for page in self.listPages(remote_dir):
			self.getPersistentIndex(page, mode='r')
			update_index = self.updateIndex(page, mode='r')
			if update_index and self.base_relay.exists(update_index):
				try:
					self.base_relay._get(update_index, tmp)
				except ExpressInterrupt:
					raise
				except Exception as exc:
					self.logger.warning("failed to retrieve update index for page '%s'", page)
					self.logger.debug(exc)
					self.logger.debug(traceback.format_exc())
					raise # for debugging
				else:
					files, _ = read_index(tmp)
					ready.append(files.keys())
			else:
				ready.append(self.index[page].keys())
		self.base_relay.delTemporaryFile(tmp)
		if ready:
			return list(itertools.chain(*ready))
		else:
			return []

	def listCorrupted(self, remote_dir='', recursive=True):
		return self.base_relay.listCorrupted(remote_dir, recursive=False)

	def listTransferred(self, remote_dir='', end2end=True, recursive=True):
		# this runs at the beginning of manager.upload;
		# clear update caches if manager.download was called
		for page in self.archive:
			if self.archive[page] and os.path.exists(self.archive[page]):
				shutil.rmtree(self.archive[page])
		#
		files = []
		for page in self.listPages(remote_dir):
			self.getPersistentIndex(page, mode='w')
			all_files = self.index[page].keys()
			if end2end:
				raise NotImplementedError
			else:
				files.append(all_files)
		if files:
			return list(itertools.chain(*files))
		else:
			return []

	def open(self):
		self.base_relay.open()

	def close(self):
		for page in self.archive:
			if self.archive[page] and os.path.exists(self.archive[page]):
				shutil.rmtree(self.archive[page])
		self.base_relay.close()

	def repair(self, lock, local_file):
		self.base_relay.repair(lock, local_file)

