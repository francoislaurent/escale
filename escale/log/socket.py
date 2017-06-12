# -*- coding: utf-8 -*-

# Copyright © 2001-2017 Python Software Foundation; All Rights Reserved
# See "PSF LICENSE AGREEMENT FOR PYTHON 2.7.13" at the following URL:
# "https://docs.python.org/2/license.html#psf-license-agreement-for-python-release"

# Copyright © 2017, François Laurent
#    Contribution: search for available port in `SocketListener`

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


"""
Borrowed from `logging-cookbook.html#network-logging <https://docs.python.org/2/howto/logging-cookbook.html#network-logging>`_.
"""

import logging, logging.handlers
import pickle
import SocketServer
import struct
import select
from escale.log import Listener


class LogRecordStreamHandler(SocketServer.StreamRequestHandler):
	"""Handler for a streaming logging request.

	This basically logs the record using whatever logging policy is
	configured locally.
	"""

	def handle(self):
		"""
		Handle multiple requests - each expected to be a 4-byte length,
		followed by the LogRecord in pickle format. Logs the record
		according to whatever policy is configured locally.
		"""
		while True:
			chunk = self.connection.recv(4)
			if len(chunk) < 4:
				break
			slen = struct.unpack('>L', chunk)[0]
			chunk = self.connection.recv(slen)
			while len(chunk) < slen:
				chunk = chunk + self.connection.recv(slen - len(chunk))
			obj = self.unPickle(chunk)
			record = logging.makeLogRecord(obj)
			self.handleLogRecord(record)

	def unPickle(self, data):
		return pickle.loads(data)

	def handleLogRecord(self, record):
		logger = logging.getLogger(record.name)
		# N.B. EVERY record gets logged. This is because Logger.handle
		# is normally called AFTER logger-level filtering. If you want
		# to do filtering, do it at the client end to save wasting
		# cycles and network bandwidth!
		logger.handle(record)


class SocketListener(Listener, SocketServer.ThreadingTCPServer):
	"""
	Simple TCP socket-based logging receiver suitable for testing.
	"""

	allow_reuse_address = 1

	def __init__(self, host='localhost',
			port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
			handler=LogRecordStreamHandler):
		self.port = port
		while True:
			try:
				SocketServer.ThreadingTCPServer.__init__(self, (host, self.port), handler)
			except Exception as e: # cannot catch socket.error
				try:
					error_code = e.errno
				except:
					raise e
				else:
					if error_code == 98:
						# socket.error: [Errno 98] Address already in use
						self.port += 1
					else:
						raise e
			else:
				break
		self.timeout = 1

	def _listen(self):
		rd, wr, ex = select.select([self.socket.fileno()], [], [], self.timeout)
		if rd:
			self.handle_request()

