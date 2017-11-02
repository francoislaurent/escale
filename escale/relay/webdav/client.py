# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#   Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


# This code is borrowed in large parts from:
# https://github.com/amnong/easywebdav/blob/master/easywebdav/client.py

# Below follows the copyright notice of the easywebdav project:

# 		Copyright (c) 2011, Kenneth Reitz
# 		Copyright (c) 2012 year, Amnon Grossman

# 		Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

# 		THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


from escale.base.essential import asstr, quote_join, relpath
from escale.base.ssl import *
from collections import namedtuple
import os.path
import re
import xml.etree.cElementTree as xml
import requests
import itertools
import functools
try:
	from httplib import responses
except ImportError:
	from http.client import responses
try:
	from urlparse import urlparse
	from urllib import quote, unquote
except ImportError:
	from urllib.parse import urlparse, quote, unquote
import time
import logging
import OpenSSL.SSL


class UnexpectedResponse(Exception):
	def __init__(self, method=None, resource=None, actual_code=None, expected_codes=()):
		# all input arguments should be optional to make the object serializable
		self.method = method
		self.resource = resource
		if not isinstance(expected_codes, (list, tuple)):
			expected_codes = (expected_codes,)
		self.expected_codes = [ str(code) for code in expected_codes ]
		self.actual_code = actual_code

	@property
	def errno(self):
		return self.actual_code
	@errno.setter
	def errno(self, code):
		self.actual_code = code

	def __repr__(self):
		return 'UnexpectedResponse({} {}, {}, {})'.format(self.method, self.resource,
				self.actual_code, self.expected_codes)

	def __str__(self):
		if self.actual_code in responses:
			got = "'{} {}'".format(self.actual_code, responses[self.actual_code])
		else:
			got = self.actual_code
		try:
			expected = quote_join(self.expected_codes)
		except:
			expected = self.expected_codes
		return "'{} {}' returned {}; {} expected".format(self.method, self.resource,
				got, expected)


File = namedtuple('File', ['name', 'size', 'mtime', 'ctime', 'contenttype'])


def _prop(elem, name, default=None):
	child = elem.find('.//{DAV:}' + name)
	if child is None or child.text is None:
		return default
	else:
		return child.text


def _elem2file(elem, basepath=None):
	path = unquote(_prop(elem, 'href'))
	if basepath:
		path = os.path.relpath(path, basepath)
	return File(
			path,
			int(_prop(elem, 'getcontentlength', 0)),
			_prop(elem, 'getlastmodified', ''),
			_prop(elem, 'creationdate', ''),
			_prop(elem, 'getcontenttype', ''),
		)


def _emulate_infinity(ls):
	@functools.wraps(ls)
	def wrapper(self, path, recursive=False):
		if recursive and self.infinity_depth is False:
			# perform explicit recursive calls
			listing = ls(self, path, False)
			#path = os.path.join('/', asstr(path))
			return itertools.chain(listing,
				*[ _emulate_infinity(ls)(self, entry.name, True)
					for entry in listing
					if not entry.contenttype ])
		first_recursive_call = recursive and self.infinity_depth is None
		try:
			listing = ls(self, path, recursive)
		except UnexpectedResponse as e:
			if e.errno == 403:
				# the server rejects 'infinity'-depth requests
				if hasattr(self, 'logger'):
					self.logger.debug("the server rejects 'infinity'-depth PROPFIND requests")
				self.infinity_depth = False
				return _emulate_infinity(ls)(self, path, recursive)
			raise
		if first_recursive_call:
			self.infinity_depth = True
		return listing
	return wrapper



class Client(object):
	def __init__(self, baseurl, username=None, password=None,
			certificate=None, verify_ssl=None, ssl_version=None):
		self.baseurl = asstr(baseurl)
		if not re.match('https?://[a-z]', baseurl):
			raise ValueError("wrong base url: '{}'", baseurl)
		parts = self.baseurl.split('/', 3)
		try:
			# basepath does not need to be quoted
			self.basepath = '/'+parts[3]
		except IndexError:
			self.basepath = None
		else:
			self.baseurl = '/'.join(parts[:3]+[quote(parts[3])])
		self.session = requests.session()
		self.session.stream = True
		if username and password:
			self.session.auth = (username, password)
		if certificate:
			self.session.cert = certificate
		if verify_ssl is not None:
			self.session.verify = verify_ssl
		if ssl_version:
			self.session.mount('https://', make_https_adapter(parse_ssl_version(ssl_version))())
		self.infinity_depth = None
		self.download_chunk_size = 1048576
		self.retry_on_errno = [32,104,110]

	def send(self, method, target, expected_codes, context=False, allow_redirects=False,
			retry_on_status_codes=[503,504], retry_on_errno=None,
			subsequent_errors_on_retry=[], **kwargs):
		if retry_on_errno is None:
			retry_on_errno = self.retry_on_errno
		url = os.path.join(self.baseurl, quote(asstr(target)))
		counter = 0
		while True:
			counter += 1
			try:
				response = self.session.request(method, url, allow_redirects=allow_redirects, **kwargs)
			except requests.exceptions.ConnectionError as e:
				while isinstance(e, Exception) and e.args:
					if e.args[1:] and isinstance(e.args[1], OSError):
						e1 = e.args[1]
						try:
							if e1.args[0] in retry_on_errno:
								if hasattr(self, 'logger'):
									logger = self.logger
								else:
									logging.getLogger()
								logger.debug('on %s %s', method, target)
								logger.debug('ignoring %s error: %s', e1.args[0], e1)
								continue
						except AttributeError:
							pass
						raise e1
					else:
						e = e.args[0]
				raise
			except OpenSSL.SSL.SysCallError as e:
				if e.args[0] in retry_on_errno:
					if hasattr(self, 'logger'):
						logger = self.logger
					else:
						logging.getLogger()
					logger.debug('on %s %s', method, target)
					logger.debug('ignoring %s error: %s', e.args[0], e)
					continue
				raise
			status_code = response.status_code
			if status_code in retry_on_status_codes:
				response.close()
				continue
			break
		if not isinstance(expected_codes, (list, tuple)):
			expected_codes = (expected_codes,)
		if status_code not in expected_codes:
			response.close()
			if 1 < counter and status_code in subsequent_errors_on_retry and not context:
				# the request actually reached the host and may have been successful;
				# the target resource may be locked or missing, depending on the type of request;
				# if the response body is not expected (`not context`), ignore the errors
				# and try to silently return
				if hasattr(self, 'logger'):
					self.logger.debug('ignoring a %s error on retrying a %s request', status_code, method)
				pass
			else:
				raise UnexpectedResponse(method, url, status_code, expected_codes)
		if not context:
			response.close()
		return response

	def mkdirs(self, dirname):
		dirs = dirname.split('/')
		dirname = ''
		for d in dirs:
			if d:
				dirname = os.path.join(dirname, d)
				self.send('MKCOL', dirname, (201, 301, 405, 423), subsequent_errors_on_retry=(423,))

	def delete(self, target):
		self.send('DELETE', target, (200, 204, 302), subsequent_errors_on_retry=(404, 423))

	def rmdir(self, dirname):
		if not (dirname and dirname[-1] == '/'):
			dirname += '/'
		self.delete(dirname)

	def upload(self, local_path, remote_path):
		while True:
			with open(local_path, 'rb') as f:
				r = self.send('PUT', remote_path, (200, 201, 204, 400), data=f, \
					retry_on_status_codes=(302, 503, 504))
			if r.status_code != 400:
				# 400 Bad Request is Yandesk speciality
				break

	def download(self, remote_path, local_path):
		r = self.send('GET', remote_path, (200,), context=True)
		try:
			with open(local_path, 'wb') as f:
				for chunk in r.iter_content(self.download_chunk_size):
					f.write(chunk)
		finally:
			r.close()

	@_emulate_infinity
	def ls(self, remote_path, recursive=False):
		if recursive:
			depth = 'infinity'
		else:
			depth = '1'
		if recursive:
			t0 = time.time()
		r = self.send('PROPFIND', remote_path, (207, 301),
				headers={'Depth': depth}, context=True)
		if recursive and hasattr(self, 'logger'):
			t1 = time.time()
			if 300 <= t1-t0:
				if 7200 <= t1-t0:
					msg = 'remote repository listing took {:.0f} hours'.format((t1-t0)/3600)
					self.logger.warning(msg)
				#else:
				#	msg = 'efficiency warning: remote repository listing took {:.0f} minutes'.format((t1-t0)/60)
				#	self.logger.debug(msg)
		try:
			# redirect
			if r.status_code == 301:
				new_path = urlparse(response.headers['location'])
				if self.basepath:
					new_path = os.path.relpath(new_path, self.basepath)
				return self.ls(new_path, recursive=recursive)
			# parse
			doctree = xml.fromstring(r.content)
		finally:
			r.close()
		entries = [ _elem2file(elem, self.basepath)
				for elem in doctree.findall('{DAV:}response') ]
		return [ entry for entry in entries if entry.name and entry.name != '.'
				and relpath(entry.name, remote_path) != '.' ]

	def exists(self, remote_path):
		codes = (200, 301, 302, 404, 423) # 302 Moved Temporarily
		response = self.send('HEAD', remote_path, codes)
		return response.status_code not in [302, 404]

