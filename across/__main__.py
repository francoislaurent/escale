
try:
	from configparser import ConfigParser
except ImportError:
	from ConfigParser import ConfigParser
import argparse
import sys
import os

default_section = 'default'

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog='across', \
		description='ACRosS - All-Clients Relay Synchronizer', \
		epilog='See also https://github.com/francoislaurent/across')
	parser.add_argument('-c', '--config', type=str, help='path to config file')
	parser.add_argument('-d', '--daemon', action='store_true', help='runs in background as a daemon (recommended)')
	parser.add_argument('-q', '--quiet', action='store_true', help='runs silently')
	args = parser.parse_args()

	verbose = not args.quiet

	cfg_file = args.config
	if cfg_file:
		if not os.path.isfile(cfg_file):
			if verbose:
				print('file not found: {}'.format(cfg_file))
			cfg_file = None
	else:
		candidates = ['~/.config/across.conf', '~/.across', '/etc/across.conf', None]
		for cfg_file in candidates:
			if cfg_file and os.path.isfile(cfg_file):
				break
	if cfg_file:
		with open(cfg_file, 'r') as f:
			while True:
				line = f.readline()
				stripped = line.strip()
				if stripped and stripped[0] == '#':
					stripped = ''
				if stripped:
					break
			cfg = [ line ] + f.readlines()
		config = ConfigParser(default_section=default_section)
		config.read_string(cfg)
		if args.quiet:
			config.set(default_section, 'verbose', False)
		if args.daemon:
			config.set(default_section, 'daemon', True)
		out = main(config)
	else:
		if verbose:
			out = 'cannot find a valid configuration file'
		else:
			out = 0
	sys.exit(out)


def main(config):
	
