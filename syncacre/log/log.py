
import logging, logging.config, logging.handlers
import os
try:
	from configparser import NoOptionError
except ImportError:
	from ConfigParser import NoOptionError

from syncacre.base import default_section



log_root = 'syncacre'



def set_logger(cfg_file, config, args, msgs=[]):
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
		file_level = "DEBUG"
	else:
		if file_level not in LOG_LEVELS:
			msgs.append(("wrong log level '%s'", file_level))
			file_level = "DEBUG"
	# console log
	if args['quiet']:
		console_level = "CRITICAL"
	else:
		console_level = "INFO"
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
				'maxBytes': 102400,
				'backupCount': 3,
				'level': file_level,
				'formatter': 'detailed'}},
		'loggers': {
			log_root: {
				'handlers': ['file', 'console']}}}
	logging.config.dictConfig(log_config)
	return (logging.getLogger(log_root), msgs)



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

	__slots__ = Listener.__slots__ + [ 'queue' ]

	def __init__(self, queue):
		self.queue = queue

	def _listen(self):
		record = self.queue.get()
		if record is None:
			raise ListenerAbort
		logger = logging.getLogger(record.name)
		logger.handle(record)

