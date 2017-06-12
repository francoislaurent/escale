# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.relay.localmount import LocalMount
from .migration import *
from escale.log import log_root
import logging
import tempfile
import tarfile


backup_logger = 'backup'


class Backup(LocalMount):

	def __init__(self, directory, **super_args):
		LocalMount.__init__(self, backup_logger, 'localhost', directory, **super_args)

	def acquireLock(*args, **kwargs):
		return True

	def releaseLock(*args, **kwargs):
		return True



def backup_manager(archive, repository, backup_or_restore='backup', config=None, logger=None):
	# load configuration file
	if config:
		msgs = []
	else:
		config, _, msgs = parse_cfg()
	# set logger
	if logger is None:
		logger, msgs = set_logger(config, msgs=msgs)
	# flush messages
	flush_init_messages(logger, msgs)
	relay_class, relay_config = parse_section(config, repository, logger)
	client = relay_config.pop('clientname')
	address = relay_config.pop('address')
	directory = relay_config.pop('directory')
	relay_logger = logger.getChild(repository)
	relay_logger.setLevel(logging.DEBUG)
	backup_logger = logger.getChild(backup_logger)
	backup_logger.setLevel(logging.DEBUG)
	relay = relay_class(client, address, directory, logger=relay_logger, **relay_config)
	if backup_or_restore == 'backup':
		errors = backup_relay_repository(relay, archive, logger=backup_logger)
	elif backup_or_restore == 'restore':
		errors = restore_relay_repository(relay, archive, logger=backup_logger)
	else:
		msg = "unsupported value '{}'".format(backup_or_restore)
		logger.error(msg)
		raise ValueError(msg)
	if errors:
		msg = "here follows a list of possibly missing files:{}".format('\n'.join(errors))
		logger.info(msg)
		raise RuntimeError(msg)


def backup_relay_repository(relay, archive, logger=None):
	ext = os.path.splitext(archive)
	if ext:
		compression = ext[1:]
		if compression == 'tar':
			compression = ''
		elif compression not in ['gz', 'bz2']:
			raise ValueError("compression not supported: '{}'".format(compression))
	else:
		compression = 'bz2'
		archive += '.tar.bz2'
	if ext == '.tar':
		compression = ''
	elif ext == '.gz':
		compression = ':gz'
	elif ext == '.bz2':
		compression = ':bz2'
	if not logger:
		logger = logging.getLogger(log_root).getChild(backup_logger)
		logger.setLevel(logging.DEBUG)
	copy_attributes = ['_placeholder_prefix', '_placeholder_suffix',
			'_lock_prefix', '_lock_suffix',
			'_message_prefix', '_message_suffix',
			'_message_hash']
	directory = tempfile.mkdtemp()
	backup = Backup(directory, logger=logger)
	try:
		for a in copy_attributes:
			setattr(backup, a, getattr(relay, a))
		errors = inter_relay_copy(relay, backup)
		with tarfile.open(archive, mode='w:'+compression) as tar:
			for member in os.listdir(directory):
				tar.add(os.path.join(directory, member), recursive=True)
	finally:
		# delete directory
		backup.purge()
		backup.close()
	return errors


def restore_relay_repository(relay, archive, logger=None):
	if not logger:
		logger = logging.getLogger(log_root).getChild(backup_logger)
		logger.setLevel(logging.DEBUG)
	directory = tempfile.mkdtemp()
	backup = Backup(directory, logger=logger)
	copy_attributes = ['_placeholder_prefix', '_placeholder_suffix',
			'_lock_prefix', '_lock_suffix',
			'_message_prefix', '_message_suffix',
			'_message_hash']
	try:
		for a in copy_attributes:
			setattr(backup, a, getattr(relay, a))
		with tarfile.open(archive, mode='r') as tar:
			tar.extractall(directory)
		errors = inter_relay_copy(backup, relay)
	finally:
		# delete directory
		backup.purge()
		backup.close()
	return errors

