# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.exceptions import QuotaExceeded
from escale.base.timer import Clock
from escale.base.config import storage_space_unit
import time
import os


class TimeQuotaController(object):
	"""
	Time and quota controller.

		refresh (int): maximum refresh interval in seconds.

		quota (int or float): maximum used space on relay host, in MB.

	"""
	def __init__(self, refresh=True, quota=None, quota_read_interval=None, quota_read_callback=None,
			logger=None):
		self.logger = logger
		if isinstance(refresh, bool) and refresh:
			refresh = 30 # seconds
		self.clock = Clock(initial_delay=refresh/2, max_delay=refresh)
		if isinstance(quota, tuple):
			value, unit = quota
			if unit:
				try:
					quota = value * storage_space_unit[unit]
				except KeyError:
					msg = "unsupported storage space unit '{}'".format(unit)
					if self.logger is not None:
						self.logger.error(msg)
					else:
						print(msg)
					#raise ValueError(msg)
					quota = None
			else:
				quota = value
		self.quota = quota
		self._quota_read_time = 0
		if quota_read_interval is None:
			self.quota_read_interval = 300
		else:
			self.quota_read_interval = quota_read_interval
		if quota_read_callback is None:
			def _callback():
				return (None, None)
			self.quota_read_callback = _callback
		else:
			self.quota_read_callback = quota_read_callback
		#self._max_space = None # attribute will be dynamically created
		self._used_space = None

	def wait(self):
		if self.clock is None:
			return False
		else:
			try:
				self.clock.wait(self.logger)
			except StopIteration:
				return False
			else:
				return True

	def pull(self, local_file):
		return self

	def push(self, local_file, callback=None):
		# check disk usage
		read_storage_space = True
		if self.quota_read_interval:
			t = time.time()
			read_storage_space = self.quota_read_interval < t - self._quota_read_time
			if read_storage_space:
				self._quota_read_time = t
		if read_storage_space:
			# update
			if callback is None:
				callback = self.quota_read_callback
			self._used_space, self._max_space = callback()
		ok = True
		if self._used_space is not None:
			if self.quota and self._max_space:
				quota = min(self._max_space, self.quota)
			else:
				quota = self.quota
			if quota:
				try: # if os.DirEntry
					s = local_file.stat()
				except AttributeError:
					s = os.stat(local_file)
				additional_space = float(s.st_size)
				additional_space /= 1048576 # in MB
				expected = self._used_space + additional_space
				ok = expected < quota
				if ok:
					self._used_space = expected
		if not ok:
			raise QuotaExceeded(self._used_space, quota)
		return self

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		pass



usage_statistics_prefix = 'us'


class History(TimeQuotaController):

	def __init__(self, repository=None, persistent=None, **super_args):
		TimeQuotaController.__init__(self, **super_args)
		self.repository = repository
		self.persistent = persistent


