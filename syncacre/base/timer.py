# -*- coding: utf-8 -*-

from math import *
import time

class Clock(object):
	__slots__ = ['count', 'cumulated_time',
			'initial_delay', 'timeout', 'max_count',
			'precision', 'bias', 'factor']

	def __init__(self, initial_delay, max_delay=None, timeout=None, max_count=None, initial_factor=2.0):
		self.initial_delay = initial_delay
		self.max_count = max_count
		if max_delay is None:
			if self.max_count:
				max_delay = self.initial_delay
			else:
				max_delay = 10.0 * self.initial_delay
		#elif isinstance(max_delay, int):
		#	max_delay = float(max_delay)
		self.precision = 10.0 ** floor(log10(self.initial_delay))
		self.timeout = timeout
		b = 1.0
		self.factor = max_delay / self.initial_delay - b
		self.bias = self.factor / (initial_factor - b) - 1
		self.__iter__()

	def __iter__(self):
		self.count = 0.0
		self.cumulated_time = 0.0
		return self

	def next(self):
		if not(self.max_count is None or self.count < self.max_count):
			raise StopIteration
		b = 1.0
		t = self.initial_delay * (b + self.count / (self.bias + self.count) * self.factor)
		if self.precision:
			t = round(t / self.precision) * self.precision
		self.cumulated_time += t
		if self.timeout is not None and self.timeout < self.cumulated_time:
			raise StopIteration
		self.count += 1.0
		return t

	def wait(self, logger=None):
		delay = self.next()
		if logger is not None:
			logger.debug('sleeping %s seconds', delay)
		time.sleep(delay)

