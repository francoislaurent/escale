# -*- coding: utf-8 -*-

# Copyright (c) 2017, François Laurent

from syncacre.log.log import Listener, ListenerAbort
from multiprocessing import Lock, Queue
from .auth import request_credential
try:
	import Queue as queue # Py2
except ImportError:
	import queue # Py3
import traceback


cli_switch = {
	'request_credential': request_credential
	}


class DirectController(object):

	def __init__(self, logger=None, maintainer=None):
		self.logger = logger
		self.maintainer = maintainer

	def requestCredential(self, hostname=None, username=None):
		return request_credential(hostname, username)

	def getServerCertificate(self, ssl_socket):
		return False # not implemented yet

	def notifyShutdown(self, backtrace):
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
				msg_body = "'{}' hit the following error and aborted:\n\n{}".format( \
						self.logger.name, backtrace)
			except:
				self.logger.error('cannot format backtrace') # very unlikely
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


class UIController(Listener, DirectController):

	def __init__(self, lock=Lock(), queue=Queue(), logger=None, maintainer=None):
		Listener.__init__(self)
		DirectController.__init__(self, logger=logger, maintainer=maintainer)
		self.lock = lock
		self.queue = queue

	@property
	def conn(self):
		return (self.lock, self.queue)

	def _listen(self):
		request = self.queue.get()
		if request is None:
			raise ListenerAbort
		elif isinstance(request, tuple):
			args = request[1:]
			request = request[0]
		fun = cli_switch[request]
		try:
			response = fun(*args)
		except KeyboardInterrupt as e:
			self.queue.put_nowait(e)
		else:
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

