# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.base.essential import PROGRAM_NAME
from syncacre.base.exceptions import *
from syncacre.log.log import Listener, ListenerAbort
from multiprocessing import Lock, Queue
from .auth import request_credential
try:
	import Queue as queue # Py2
except ImportError:
	import queue # Py3
import traceback
import time


cli_switch = {
	'request_credential': request_credential,
	}


class DirectController(object):

	def __init__(self, logger=None, maintainer=None):
		self.logger = logger
		self.maintainer = maintainer

	def requestCredential(self, hostname=None, username=None):
		return request_credential(hostname, username)

	def getServerCertificate(self, ssl_socket):
		return False # not implemented yet

	def notifyMaintainer(self, exception='', backtrace=''):
		if self.maintainer:
			# try to email the maintainer about the unexpected shutdown
			try:
				import socket
				hostname = socket.gethostname()
			except:
				hostname = 'localhost'
			try:
				sender = '{}@{}'.format(self.logger.name, hostname)
			except:
				#self.logger.debug('cannot format sender') # logger might be corrupted
				return
			else:
				self.logger.debug("emailing '%s' from '%s'", self.maintainer, sender)
			try:
				msg_body = "'{}' hit the following error and aborted:\n\n{}\n\n{}".format( \
						self.logger.name, exception, backtrace)
			except:
				self.logger.error('cannot format exception or backtrace') # very unlikely
				return
			try:
				import smtplib
				server = smtplib.SMTP(hostname)
			except: # [Errno 111] Connection refused
				self.logger.warning("failed to connect to SMTP server at '%s'", hostname)
				self.logger.debug(traceback.format_exc())
				return
			try:
				server.sendmail(sender,	self.maintainer, msg_body)
			except:
				self.logger.warning("failed to email '%s'", self.maintainer)
				self.logger.debug(traceback.format_exc())
			finally:
				server.quit()

	def failure(self, repository, exception, backtrace=None):
		if isinstance(exception, UnrecoverableError):
			self.logger.critical("UnrecoverableError: %s", exception.args[0])
			if backtrace is not None:
				self.logger.critical(" %s", backtrace)
			self.logger.critical("the Python environment should be reset")
		if self.maintainer:
			self.notifyMaintainer(exception, backtrace)

	def success(self, repository, result):
		pass

	def restartWorker(self, repository, sleep_time=None):
		if sleep_time:
			if 1 < sleep_time:
				number = 's'
			else:
				number = ''
			self.logger.info("restarting %s for '%s' in %s second%s",
				PROGRAM_NAME, repository, sleep_time, number)
			time.sleep(sleep_time)
		else:
			self.logger.info("restarting %s for '%s'", PROGRAM_NAME, repository)


class UIController(Listener, DirectController):

	def __init__(self, lock=Lock(), queue=Queue(), logger=None, parent=None, maintainer=None):
		Listener.__init__(self)
		DirectController.__init__(self, logger=logger, maintainer=maintainer)
		self.lock = lock
		self.queue = queue
		self.parent = parent

	@property
	def conn(self):
		return (self.lock, self.queue)

	def _listen(self):
		"""
		Protocol:

			* ``[expect_response, ]function_name[, function_argument]*``
			* ``expect_response`` is `bool` or `int` (default ``True``)
		"""
		request = self.queue.get()
		if request is None:
			raise ListenerAbort
		elif isinstance(request, tuple):
			if isinstance(request[0], (bool, int)):
				function_index = 1
				expect_response = request[0]
			else:
				function_index = 0
				expect_response = True
			args = request[function_index+1:]
			function_name = request[function_index]
		try:
			fun = cli_switch[function_name]
		except KeyError:
			fun = getattr(self, function_name)
		try:
			response = fun(*args)
		except (KeyboardInterrupt, SystemExit):
			raise
		except Exception as exc:
			response = exc
		if expect_response:
			self.queue.put(response)

	def abort(self):
		Listener.abort(self)
		try:
			self.queue.put_nowait(None)
		except queue.Full:
			pass

	def requestCredential(self, hostname=None, username=None):
		request = ('request_credential', hostname, username)
		with self.lock:
			self.queue.put(request)
			response = self.queue.get()
		if isinstance(response, Exception):
			raise response
		return response

	def failure(self, *args):
		DirectController.failure(self, *args)
		return self.__signal__('_failure', args)

	def _failure(self, *args):
		self.parent.put(args)
		return True

	def success(self, *args):
		return self.__signal__('_success', args)

	def _success(self, *args):
		self.parent.put(args)
		return True

	def __signal__(self, method_name, arguments):
		if self.parent is None:
			request = (False, method_name) + arguments
			with self.lock:
				self.queue.put(request)
		else:
			return getattr(self, method_name)(*arguments)

	def __request__(self, method_name, arguments):
		if self.parent is None:
			request = (method_name,) + arguments
			with self.lock:
				self.queue.put(request)
				response = self.queue.get()
		else:
			response = getattr(self, method_name)(*arguments)
		return response


