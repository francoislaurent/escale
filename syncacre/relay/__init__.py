
from .relay import AbstractRelay, Relay

__all__ = ['AbstractRelay', 'Relay']

__protocols__ = []

try:
	from .ftp import FTP
	__all__.append('FTP')
	__protocols__.append(FTP)
except ImportError as e:
	print(e)
	pass

try:
	from .ssh import SSH
	__all__.append('SSH')
	__protocols__.append(SSH)
except ImportError as e:
	print(e)
	pass

try:
	from .webdav import WebDAV
	__all__.append('WebDAV')
	__protocols__.append(WebDAV)
except ImportError as e:
	print(e)
	pass


def by_protocol(protocol):
	for p in __protocols__[::-1]:
		if isinstance(p.__protocol__, list):
			if protocol in p.__protocol__:
				return p
		elif protocol == p.__protocol__:
			return p
	raise KeyError('cannot find protocol {}'.format(protocol))


__all__ += ['__protocols__', 'by_protocol']

