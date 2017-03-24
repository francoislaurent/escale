

import time
import os


class Manager(object):

	def __init__(self, relay, path=None, address=None, directory=None, mode=None, \
		encryption=None, passphrase=None, \
		refresh=None, **relay_args):
		self.path = path
		self.dir = directory
		self.mode = mode
		self.encryption = encryption
		self.passphrase = passphrase
		self.refresh = refresh
		self.relay = relay(address, **relay_args)

	def run(self):
		self.relay.open()
		try:
			while True:
				if self.mode is None or self.mode == 'download':
					remote = self.relay.listReady(self.dir)
					for filename in remote:
						filepath = os.path.join(self.dir, filename)
						self.relay.safePop(filepath, self.path)
						# TODO: decipher file
				if self.mode is None or self.mode == 'upload':
					local = os.listdir(self.path)
					remote = self.relay.listTransfered(self.dir, end2end=False)
					print(remote)
					for filename in local:
						if filename not in remote:
							filepath = os.path.join(self.path, filename)
							# TODO: check disk usage on relay
							# TODO: encrypt file
							self.relay.safePush(filepath, self.dir)
				if self.refresh:
					time.wait(self.refresh)
				else:
					break
		except KeyboardInterrupt:
			pass
		self.relay.close()


