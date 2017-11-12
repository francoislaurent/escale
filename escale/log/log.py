# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


import logging, logging.config, logging.handlers
import os
try:
	from configparser import NoOptionError
except ImportError:
	from ConfigParser import NoOptionError

from escale.base.essential import PROGRAM_NAME
from escale.base.config import default_section



log_root = PROGRAM_NAME



def set_logger(config, cfg_file=None, verbosity=logging.NOTSET, msgs=[]):
	if not cfg_file:
		cfg_file = config.filename
	# log file
	try:
		log_file = config.get(default_section, 'log file')
	except NoOptionError:
		log_file, _ = os.path.splitext(cfg_file)
		log_file = '{}.log'.format(log_file)
	if log_file.startswith('/etc'):
		log_file = './log'
		msgs.append((logging.INFO, "logging in '{}' (fallback)", log_file))
	try:
		file_level = config.get(default_section, 'log level').upper()
	except NoOptionError:
		file_level = 'DEBUG'
	else:
		LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
		if file_level not in LOG_LEVELS:
			msgs.append(("wrong log level '%s'", file_level))
			file_level = 'DEBUG'
	try:
		rotate_count = config.getint(default_section, 'log rotate')
	except NoOptionError:
		rotate_count = 3
	# console log
	console_default = 'INFO'
	if verbosity == 1:
		# handles `bool`s (all possible values), some `int`s and `float`s
		# but 0 because 0 is the default value
		if verbosity:
			console_level = console_default
		else:
			console_level = 'CRITICAL'
	elif isinstance(verbosity, str):
		console_level = verbosity
	else: # verbosity is `int` or `float`
		if not isinstance(verbosity, int):
			verbosity = int(verbosity)
		console_level = {
				logging.NOTSET:	console_default,
				logging.DEBUG:	'DEBUG',
				logging.INFO:	'INFO',
				logging.WARNING:	'WARNING',
				logging.ERROR:	'ERROR',
				logging.CRITICAL:	'CRITICAL'
			}[verbosity]
	#
	log_config = {
		'version': 1,
		'formatters': {
			'detailed': {
				'class': 'logging.Formatter',
				'format': '%(asctime)s %(name)s[%(levelname)s]\t%(module)s.%(funcName)s:%(lineno)s\t%(message)s',
				'datefmt': '%d/%m %H:%M'},
			'default': {
				'class': 'logging.Formatter',
				'format': '%(levelname)s[%(name)s]:%(module)s.%(funcName)s: %(message)s'}},
		'handlers': {
			'console': {
				'class': 'logging.StreamHandler',
				'level': console_level,
				'formatter': 'default'},
			'file': {
				'class': 'logging.handlers.RotatingFileHandler',
				'filename': log_file,
				'maxBytes': 1048576,
				'backupCount': rotate_count,
				'level': file_level,
				'formatter': 'detailed'}},
		'loggers': {
			log_root: {
				'handlers': ['file', 'console']}}}
	logging.config.dictConfig(log_config)
	root = logging.getLogger(log_root)
	root.setLevel(logging.DEBUG)
	return (root, msgs)


def flush_init_messages(logger, msgs):
	for msg in msgs:
		if isinstance(msg, tuple):
			if isinstance(msg[0], str):
				logger.warning(*msg)
			else: # msg[0] is log level
				logger.log(*msg)
		else:
			logger.warning(msg)



class ListenerAbort(Exception):
	pass


class Listener(object):
	__slots__ = [ '_active' ]

	def _listen(self):
		raise NotImplementedError('abstract method')

	def listen(self):
		self._active = True
		try:
			while self._active:
				self._listen()
		except ListenerAbort:
			self.abort()

	def abort(self):
		self._active = False


class QueueListener(Listener):

	__slots__ = [ 'queue' ]

	def __init__(self, queue):
		self.queue = queue

	def _listen(self):
		record = self.queue.get()
		if record is None:
			raise ListenerAbort
		logger = logging.getLogger(record.name)
		logger.handle(record)

