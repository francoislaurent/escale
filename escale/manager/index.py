# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import *
from .manager import Manager
from ..base.config import storage_space_unit
from ..relay.info import Metadata, parse_metadata
from ..relay.index import AbstractIndexRelay
import os
import bz2
import shutil
import tarfile
import tempfile
from collections import defaultdict


class IndexManager(Manager):

	def __init__(self, relay, *args, **kwargs):
		#if not isinstance(relay, AbstractIndexRelay):
		#	raise TypeError("relay is not an IndexRelay")
		max_page_size, max_page_size_unit = kwargs.pop('maxpagesize', (200, None))
		if max_page_size_unit:
			max_page_size = max_page_size * storage_space_unit[max_page_size_unit] * 1048576
		Manager.__init__(self, relay, *args, **kwargs)
		self.max_page_size = max_page_size
		self.extraction_repository = tempfile.mkdtemp()

	def terminate(self, pullers):
		return self.count <= len(pullers)

	def __del__(self):
		try:
			shutil.rmtree(self.extraction_repository)
		except AttributeError:
			# exception raised in __init__
			pass
		#Manager.__del__(self)

	def sanityChecks(self):
		self.relay.repairUpdates()
		Manager.sanityChecks(self)
		self.relay.clearIndex()

	def download(self):
		new = False
		for page in self.relay.listPages():
			index_loaded = self.relay.loaded(page)
			with self.relay.getUpdate(page, self.terminate) as update:
				get_files = []
				for remote_file in update:
					dirname, basename = os.path.split(remote_file)
					if not self._filter(basename):
						continue
					if dirname and not self._filter_directory(dirname):
						continue
					resource = remote_file
					local_file = self.repository.writable(resource, absolute=True)
					if not local_file:
						# update not allowed
						continue
					metadata = parse_metadata(update[remote_file])
					last_modified = None
					if self.timestamp:
						if metadata and metadata.timestamp:
							last_modified = metadata.timestamp
						else:
							# if `timestamp` is `True` or is a format string,
							# then metadata should be defined
							self.logger.warning("corrupt meta information for file '%s'", remote_file)
					if os.path.isfile(local_file):
						if not metadata:
							self.logger.warning("missing meta information for file '%s'", remote_file)
							continue
						# generate checksum of the local file
						checksum = self.checksum(resource)
						# check for modifications
						if not metadata.fileModified(local_file, checksum, remote=True, debug=self.logger.debug):
							if index_loaded:
								extracted_file = join(self.extraction_repository, remote_file)
								self.logger.info("deleting duplicate or outdated file '%s'", remote_file)
								try:
									os.unlink(extracted_file)
								except (IOError, OSError) as e:#FileNotFoundError:
									# catch FileNotFoundError (does not exist in Python2)
									if e.errno == errno.ENOENT:
										self.logger.debug("file '%s' not found", extracted_file)
									else:
										raise
							continue
					get_files.append((remote_file, local_file, last_modified))
				if get_files:
					new = True
					missing = []
					if self.relay.hasUpdate(page):
						try:
							fd, archive = tempfile.mkstemp()
							os.close(fd)
							encrypted = self.encryption.prepare(archive)
							with self.tq_controller.pull(encrypted):
								self.logger.debug("downloading update data for page '%s'", page)
								self.relay.getUpdateData(page, encrypted)
							while not os.path.exists(encrypted):
								pass
							self.encryption.decrypt(encrypted, archive)
							try:
								with tarfile.open(archive, mode='r:bz2') as tar:
									tar.extractall(self.extraction_repository)
							except Exception as e: # ReadError: not a bzip2 file
								self.logger.error("%s", e)
								missing = [ m for m, _, _ in get_files ]
						finally:
							os.unlink(archive)
					else:
						missing = [ m for m, _, _ in get_files ]
					if not missing:
						for remote, local, mtime in get_files:
							dirname = os.path.dirname(local)
							if dirname and not os.path.isdir(dirname):
								os.makedirs(dirname)
							extracted = join(self.extraction_repository, remote)
							try:
								shutil.move(extracted, local)
							except IOError as e:#FileNotFoundError:
								# catch FileNotFoundError (does not exist in Python2)
								if e.errno == errno.ENOENT:
									self.logger.debug("file '%s' not found", extracted)
									#self.logger.info("failed to download file '%s'", remote)
									missing.append(remote)
								else:
									raise
							else:
								self.logger.info("file '%s' successfully downloaded", remote)
								if mtime:
									# set last modification time
									os.utime(local, (time.time(), mtime))
					if missing:
						self.relay.requestMissing(page, missing)
		new |= Manager.download(self)
		return new

	def upload(self):
		new = False
		indexed = defaultdict(list)
		not_indexed = []
		for resource in self.localFiles():
			remote_file = resource
			if self.relay.indexed(remote_file):
				indexed[self.relay.page(remote_file)].append(resource)
			else:
				not_indexed.append(resource)
		#
		for page in indexed:
			try:
				push = []
				pushed = []
				with self.relay.setUpdate(page) as update:
					page_index = self.relay.getPageIndex(page)
					update_index = {}
					for resource in indexed[page]:
						remote_file = resource
						local_file = self.repository.absolute(resource)
						checksum = self.checksum(resource)
						try:
							page_metadata = parse_metadata(page_index[remote_file])
						except KeyError:
							pass
						else:
							if (self.timestamp or self.hash_function) and \
								not page_metadata.fileModified(local_file, checksum, remote=False, debug=self.logger.debug):
								continue
						try:
							last_modified, _ = self.checksum_cache[resource]
						except AttributeError:
							last_modified = os.path.getmtime(local_file)
						metadata = Metadata(target=remote_file, timestamp=last_modified, checksum=checksum, pusher=self.relay.client)
						push.append((local_file, remote_file, metadata))
					if push:
						new = True
						fd, archive = tempfile.mkstemp()
						os.close(fd)
						try:
							size = 0
							with tarfile.open(archive, mode='w:bz2') as tar:
								for local_file, remote_file, metadata in push:
									tar.add(local_file, arcname=remote_file, recursive=True)
									update[remote_file] = metadata
									pushed.append((local_file, remote_file))
									size += os.stat(local_file).st_size
									if self.max_page_size < size:
										break
							final_file = self.encryption.encrypt(archive)
							while True:
								try:
									with self.tq_controller.push(archive):
										self.logger.debug("uploading update data for page '%s'", page)
										self.relay.setUpdateData(page, final_file)
								except QuotaExceeded as e:
									self.logger.info("%s; no more files can be sent", e)
									if not self.tq_controller.wait():
										raise
								else:
									break
							self.encryption.finalize(final_file)
						finally:
							os.unlink(archive)
					else:
						assert not update
				for _, remote_file in pushed:
					self.logger.info("file '%s' successfully uploaded", remote_file)
			except PostponeRequest:
				continue
		#
		remote = self.relay.listTransferred('', end2end=False)
		for resource in not_indexed:
			remote_file = resource
			local_file = self.repository.absolute(resource)
			if PYTHON_VERSION == 2 and isinstance(remote_file, unicode) and \
				remote and isinstance(remote[0], str):
				remote_file = remote_file.encode('utf-8')
			exists = remote_file in remote
			checksum = self.checksum(resource)
			modified = False # if no remote copy, this is ignored
			if (self.timestamp or self.hash_function) and exists:
				# check file last modification time and checksum
				meta = self.relay.getMetadata(remote_file, timestamp_format=self.timestamp)
				if meta:
					modified = meta.fileModified(local_file, checksum, remote=False, debug=self.logger.debug)
				else:
					# no meta information available
					modified = True
					# this may not be true, but this will update the meta
					# information with a valid content.
			if not exists or modified:
					with self.repository.confirmPush(resource):
						new = True
						last_modified = os.path.getmtime(local_file)
						temp_file = self.encryption.encrypt(local_file)
						self.logger.info("uploading file '%s'", remote_file)
						try:
							with self.tq_controller.push(local_file):
								ok = self.relay.push(temp_file, remote_file, blocking=False,
									last_modified=last_modified, checksum=checksum)
						except QuotaExceeded as e:
							self.logger.info("%s; no more files can be sent", e)
							ok = False
						finally:
							self.encryption.finalize(temp_file)
						if ok:
							self.logger.debug("file '%s' successfully uploaded", remote_file)
						elif ok is not None:
							self.logger.warning("failed to upload '%s'", remote_file)
		return new

	def localFiles(self, path=None):
		return Manager.localFiles(self, path)

