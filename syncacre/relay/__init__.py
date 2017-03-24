
from .interface import Interface

__all__ = ['__protocols__', 'by_protocol']

__protocols__ = []

try:
	from .ssh import SSH
	__all__.append('SSH')
	__protocols__.append(SSH)
except ImportError:
	pass

try:
	from .webdav import WebDAV
	__all__.append('WebDAV')
	__protocols__.append(WebDAV)
except ImportError:
	pass


def by_protocol(protocol):
	for p in __protocols__.reverse():
		if isinstance(p.__protocol__, list):
			if protocol in p.__protocol__:
				return p
		elif protocol == p.__protocol__:
			return p
	raise KeyError('cannot find protocol {}'.format(protocol))


