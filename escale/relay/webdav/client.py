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


from escale.base.essential import asstr, quote_join
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


class UnexpectedResponse(Exception):
	def __init__(self, method, resource, actual_code, expected_codes=()):
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
	return default if child is None else child.text


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

	def send(self, method, target, expected_codes, context=False, allow_redirects=False, **kwargs):
		url = os.path.join(self.baseurl, quote(asstr(target)))
		try:
			response = self.session.request(method, url, allow_redirects=allow_redirects, **kwargs)
		except requests.exceptions.ConnectionError as e:
			if e.args[1:] and e.args[1]:
				e1 = e.args[1]
				if isinstance(e1, OSError):# and hasattr(e1, 'errno') and e1.errno == 107:
					raise e1
			else:
				raise
		status_code = response.status_code
		if not isinstance(expected_codes, (list, tuple)):
			expected_codes = (expected_codes,)
		if status_code not in expected_codes:
			response.close()
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
				self.send('MKCOL', dirname, (201, 301, 405, 423))

	def delete(self, target):
		self.send('DELETE', target, (200, 204))

	def rmdir(self, dirname):
		if not (dirname and dirname[-1] == '/'):
			dirname += '/'
		self.delete(dirname)

	def upload(self, local_path, remote_path):
		with open(local_path, 'rb') as f:
			r = self.send('PUT', remote_path, (200, 201, 204), data=f)

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
		r = self.send('PROPFIND', remote_path, (207, 301),
				headers={'Depth': depth}, context=True)
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
				and os.path.relpath(entry.name, remote_path) != '.' ]

	def exists(self, remote_path):
		codes = (200, 301, 404, 423)
		response = self.send('HEAD', remote_path, codes)
		return response.status_code != 404

