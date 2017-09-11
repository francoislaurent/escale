# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base.essential import PROGRAM_NAME, join
from escale.base.exceptions import *
from escale.log.log import Listener, ListenerAbort
from multiprocessing import Lock, Queue
from .auth import request_credential
try:
	import Queue as queue # Py2
except ImportError:
	import queue # Py3
import traceback
import time
import importlib
import os.path


cli_switch = {
	'request_credential': request_credential,
	}

oauth_package = 'escale.oauth'


class DirectController(object):
	"""
	User interface controller.

	Implements a few basic routines that inform the user or request information from her.
	"""

	def __init__(self, logger=None, maintainer=None):
		self.logger = logger
		self.maintainer = maintainer

	@property
	def error_file(self):
		error_file = None
		try:
			for handle in self.logger.handlers:
				try:
					logfile = handle.baseFilename
				except:
					pass
				else:
					error_file = join(os.path.dirname(logfile), 'error.log')
					break
		except (AttributeError, TypeError):
			pass
		return error_file

	def requestCredential(self, hostname=None, username=None):
		"""
		Request username and password.
		"""
		return request_credential(hostname, username)

	def getServerCertificate(self, ssl_socket):
		"""
		Deprecated.
		"""
		return False # not implemented yet

	def notifyMaintainer(self, exception='', backtrace=''):
		"""
		Send a notification email to the maintainer's email address using
		the local SMTP server if any.
		"""
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
		"""
		Log and notify client about termination on error.
		"""
		if self.error_file:
			t = time.strftime('%d/%m %H:%M', time.localtime())
			try:
				with open(self.error_file, 'a') as f:
					if f.tell() == 0:
						nl = ''
					else:
						nl = '\n'
					f.write('{}{} {}:\t{}'.format(nl, t, repository, exception))
					if backtrace:
						f.write('\n{}'.format(backtrace))
			except ExpressInterrupt:
				pass
			except:
				self.logger.error('failed to log error')
		if self.maintainer:
			self.notifyMaintainer(exception, backtrace)

	def success(self, repository, result):
		"""
		Notify client about task completion.
		"""
		pass

	def restartWorker(self, repository, sleep_time=None):
		"""
		Notify client about automatic restart.
		"""
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

	def __dynamic__(self, package, protocol, function, *args, **kwargs):
		if isinstance(protocol, list):
			for p in protocol:
				try:
					module = importlib.import_module('.'.join((package, p)))
				except ImportError:
					pass
				else:
					break
		else:
			module = importlib.import_module('.'.join((package, protocol)))
		return getattr(module, function)(*args, **kwargs)

	def mount(self, protocol, *args):
		"""
		Mount volumes in the file system.
		"""
		try:
			return self.__dynamic__(oauth_package, protocol, 'mount', *args) # no kwargs
		except:
			print(traceback.format_exc())
			raise

	def umount(self, protocol, *args):
		"""
		Mount volumes from the file system.
		"""
		return self.__dynamic__(oauth_package, protocol, 'umount', *args) # no kwargs



class UIController(Listener, DirectController):
	"""
	Thread-safe version of a user interface controller.

	A "parent" UIController should run in the main thread while each worker thread or
	subprocess runs a proxy UIController that relays all the calls to the "parent"
	controller.
	"""

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
		else:
			raise ValueError('not a tuple: {}'.format(request))
		try:
			fun = cli_switch[function_name]
		except KeyError:
			fun = getattr(self, function_name)
		try:
			response = fun(*args)
		except ExpressInterrupt:
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
		return self.__signal__('_failure', args)

	def _failure(self, *args):
		DirectController.failure(self, *args)
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

	def mount(self, *args):
		return self.__request__('_mount', args)

	def _mount(self, *args):
		return DirectController.mount(self, *args)

	def umount(self, *args):
		return self.__signal__('_umount', args)

	def _umount(self, *args):
		return DirectController.umount(self, *args)

