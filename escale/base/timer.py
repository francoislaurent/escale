# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


from math import *
import time

class Clock(object):
	'''
	Generate increasing time intervals.

	Successive time intervals monotonically increase following a softsign function:
	::

		dt = dt0 * (1 +  a * n / (b + n))

	where ``dt0`` is `initial_delay`, ``a`` is `factor`, ``b`` is `bias` and ``n`` is `count`.
	
	:class:`Clock` implements the iterator interface.

	Attributes:

		count (float): number of time interval requests.

		cumulated_time (float): cumulated time in seconds.

		initial_delay (float): first time interval in seconds.

		timeout (int or float): maximum cumulated time.

		max_count (int or float): maximum number of time interval requests.

		precision (float): order at which time intervals are rounded.

		bias (float): softsign bias.

		factor (float): factor on the softsign term.

		max_delay (float, __init__ argument, not stored):
			maximum delay.

		initial_factor (float, __init__ argument, not stored):
			ratio of the second time interval over the first (or initial) one.
	'''
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
		self.precision = 10.0 ** (floor(log10(self.initial_delay)) - 1)
		self.timeout = timeout
		b = 1.0
		self.factor = max_delay / self.initial_delay - b
		if 0 < self.factor:
			self.bias = self.factor / (initial_factor - b) - 1
		else:
			# any value other than 0
			self.bias = 1.0
		self.__iter__()

	def __iter__(self):
		self.count = 0.0
		self.cumulated_time = 0.0
		return self

	def next(self):
		'''
		Generate a new time interval.

		Returns:

			float: time interval in seconds.
		'''
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
		'''
		Call :meth:`next` and sleep during the returned duration.
		'''
		delay = self.next()
		if logger is not None:
			logger.debug('sleeping %s seconds', delay)
		time.sleep(delay)

