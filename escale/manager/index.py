# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.exceptions import PostponeRequest
from .manager import Manager
from ..base.config import storage_space_unit
from ..relay.info import Metadata
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
		max_page_size, max_page_size_unit = kwargs.pop('maxpagesize', (1024, None))
		if max_page_size_unit:
			max_page_size = max_page_size * storage_space_unit[max_page_size_unit] * 1048576
		Manager.__init__(self, relay, *args, **kwargs)
		self.relay.lock_args = self.pop_args
		self.max_page_size = max_page_size
		self.extraction_repository = tempfile.mkdtemp()

	def terminate(self, count):
		return self.count <= count

	def __del__(self):
		try:
			shutil.rmtree(self.extraction_repository)
		except AttributeError:
			# exception raised in __init__
			pass

	def sanityCheck(self):
		self.relay.repairUpdates()
		self.relay.reloadIndex()
		Manager.sanityCheck(self)

	def download(self):
		new = False
		for page in self.relay.listPages():
			with self.relay.getUpdate(page, self.terminate) as update:
				get_files = []
				for remote_file in update:
					if not self._filter(remote_file):
						continue
					local_file = self.repository.writable(remote_file)
					if not local_file:
						# update not allowed
						continue
					metadata = update[remote_file]
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
						checksum = self.checksum(local_file)
						# check for modifications
						if not metadata.fileModified(local_file, checksum, remote=True, debug=self.logger.debug):
							extracted_file = join(self.extraction_repository, remote_file)
							os.unlink(extracted_file)
							continue
					get_files.append((remote_file, local_file, last_modified))
				if get_files:
					new = True
					try:
						with tempfile.NamedTemporaryFile(delete=False) as archive:
							encrypted = self.encryption.prepare(archive.name)
							with self.tq_controller.pull(encrypted):
								self.logger.debug("downloading update data for page '%s'", page)
								self.relay.getUpdateData(page, encrypted)
							self.encryption.decrypt(encrypted, archive.name)
							with tarfile.open(archive, mode='r:bz2') as tar:
								tar.extractall(self.extraction_repository)
					finally:
						os.unlink(archive)
					for remote, local, mtime in get_files:
						extracted = join(self.extraction_repository, remote)
						shutil.rename(extracted, local)
						self.logger.info("file '%s' successfully downloaded", remote)
						if mtime:
							# set last modification time
							os.utime(local, (time.time(), mtime))
		new |= Manager.download(self)
		return new

	def upload(self):
		indexed = defaultdict(dict)
		not_indexed = []
		for local_file in self.localFiles():
			remote_file = os.path.relpath(local_file, self.path) # relative path
			if self.relay.indexed(remote_file):
				indexed[self.relay.page(remote_file)][local_file] = remote_file
			else:
				not_indexed.append((local_file, remote_file))
		new = False
		for page in indexed:
			try:
				push = []
				with self.relay.setUpdate(page) as update:
					page_index = self.relay.getPageIndex(page)
					for local_file in indexed[page]:
						remote_file = indexed[page][local_file]
						checksum = self.checksum(local_file)
						try:
							page_metadata = page_index[remote_file]
						except KeyError:
							pass
						else:
							if (self.timestamp or self.hash_function) and \
								not page_metadata.fileModified(local_file, checksum, remote=False, debug=self.logger.debug):
								continue
						new = True
						last_modified = os.path.getmtime(local_file)
						update_metadata = Metadata(target=remote_file, timestamp=last_modified, checksum=checksum, pusher=self.client)
						update[remote_file] = update_metadata
						push.append((local_file, remote_file))
					if push:
						assert update
						fd, archive = tempfile.mkstemp()
						os.close(fd)
						try:
							size = 0
							with tarfile.open(archive, mode='w:bz2') as tar:
								for local_file, remote_file in push:
									tar.add(local_file, arcname=remote_file, recursive=True)
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
				for _, remote_file in push:
					self.logger.info("file '%s' successfully uploaded", remote_file)
			except PostponeRequest:
				continue
		remote = self.relay.listTransferred('', end2end=False)
		for local_file, remote_file in not_indexed:
			if PYTHON_VERSION == 2 and isinstance(remote_file, unicode) and \
				remote and isinstance(remote[0], str):
				remote_file = remote_file.encode('utf-8')
			exists = remote_file in remote
			checksum = self.checksum(local_file)
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
					with self.repository.confirmPush(local_file):
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

