# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from math import *
import time

class Clock(object):
	'''
	Generate increasing time intervals.

	Successive time intervals monotonically increase following a tanh function::

		t_n = t_0 + (t_N - t_0) / (1 + exp(N - 2*n))

	where ``t_0`` is the initial delay, ``t_n`` is the delay at iteration ``n`` 
	and ``N`` is one of the first iterations with maximum delay.
	
	:class:`Clock` implements the iterator interface.

	Attributes:

		count (float): number of time interval requests.

		max_count (int or float): maximum number of time interval requests.

		count_at_max_delay (int): ``N``.

		initial_delay (float): first time interval in seconds.

		max_delay (float): maximum delay.

		cumulated_time (float): cumulated time in seconds.

		timeout (int or float): maximum cumulated time.

		precision (float): order at which time intervals are rounded.
	'''
	__slots__ = ['count', 'max_count', 'count_at_max_delay',
			'initial_delay', 'max_delay', 'cumulated_time', 'timeout',
			'precision']

	def __init__(self, initial_delay=1, max_delay=None, timeout=None, max_count=None, count_at_max_delay=10):
		self.initial_delay = initial_delay
		self.max_count = max_count
		if max_delay is None:
			if self.max_count:
				max_delay = self.initial_delay
			else:
				max_delay = 10.0 * self.initial_delay
		self.max_delay = max_delay
		self.count_at_max_delay = count_at_max_delay
		self.precision = 10.0 ** (floor(log10(self.initial_delay)) - 1)
		self.timeout = timeout
		self.reset()

	def reset(self):
		self.count = 0
		self.cumulated_time = 0.0

	def __iter__(self):
		self.reset()
		return self

	def next(self):
		'''
		Generate a new time interval.

		Returns:

			float: time interval in seconds.
		'''
		if not(self.max_count is None or self.count < self.max_count):
			raise StopIteration
		t = self.initial_delay + (self.max_delay - self.initial_delay) / \
			(1.0 + exp(float(self.count_at_max_delay - 2 * self.count)))
		if self.precision:
			t = round(t / self.precision) * self.precision
		self.cumulated_time += t
		if self.timeout is not None and self.timeout < self.cumulated_time:
			raise StopIteration
		self.count += 1
		return t

	def wait(self, logger=None):
		'''
		Call :meth:`next` and sleep during the returned duration.
		'''
		delay = self.next()
		if self.precision:
			precision = -int(log10(self.precision))
			if precision < 0:
				precision = 0
			precision = '.{}'.format(precision)
		else:
			precision = ''
		if logger is not None:
			logger.debug('sleeping %{}f seconds'.format(precision), delay)
		time.sleep(delay)

