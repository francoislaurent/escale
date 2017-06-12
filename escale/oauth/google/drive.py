# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.relay.google.drive import *
from escale.base.subprocess import *
import os
import time


def mount(drive_bin, mount_point=None, config=None, lock=None):
	if not mount_point:
		try:
			config = config.filename
		except AttributeError:
			pass
		mount_point = os.path.join(os.path.dirname(asstr(config)), 'mount', 'GoogleDrive')
	if not os.path.isdir(mount_point):
		os.makedirs(mount_point)
	credentials = os.path.join(mount_point, '.gd', 'credentials.json')
	if os.path.exists(credentials):
		# check whether token is still valid
		try:
			with_subprocess(drive_bin, 'quota', mount_point, error=IOError)
		except IOError:
			os.unlink(credentials)
			refresh = True
		else:
			refresh = False
	else:
		refresh = True
	if refresh:
		# init calls function `RetrieveRefreshToken` in:
		# https://github.com/odeke-em/drive/blob/master/src/remote.go
		with_subprocess(drive_bin, 'init', mount_point, input=True)
		cumulated_time = 0
		time_increment = 1
		while not os.path.exists(credentials):
			time.sleep(time_increment)
			cumulated_time += time_increment
			if 10 < cumulated_time:
				raise EnvironmentError("failed to mount '{}'".format(mount_point))
		# do not pull; backend never uses the local copy in the mount
		#ls = os.listdir(mount_point)
		#if not ls[1:] and ls[0] == '.gd':
		#	with_subprocess(drive_bin, 'pull', '-no-prompt', mount_point, error=IOError)
	return mount_point

def umount(drive_bin, mount_point):
	cwd = os.getcwd()
	try:
		os.chdir(mount_point)
		with_subprocess(drive_bin, 'deinit')
	finally:
		os.chdir(cwd)

