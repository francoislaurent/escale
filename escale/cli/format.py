# -*- coding: utf-8 -*-

# Copyright © 2017, Institut Pasteur
#    Contributor: François Laurent


def quote_join(ps, final=' and ', join=', '):
	p = ["'{}'"]
	for _ in ps[1:-1]:
		p.append(join)
		p.append("'{}'")
	if ps[1:]:
		p.append(final)
		p.append("'{}'")
	return ''.join(p).format(*ps)


def decorate_line(line):
	"""
	Capitalize the first letter.
	"""
	if line:
		return line[0].upper()+line[1:]
	else:
		return line

def multiline_print(*lines):
	"""
	Decorate and print a sentence.

	The first letter of the first line is capitalized and
	a final dot is appended under some conditions.
	"""
	if not lines:
		return
	line = decorate_line(lines[0])
	if not lines[1:]:
		if line and line[0].isalpha() and line[-1].isalnum():
			line += '.'
		print(line)
		return
	print(line)
	for line in lines[1:-1]:
		print(line)
	line = lines[-1]
	if line and line[0].isalpha() and line[-1].isalnum():
		line += '.'
	print(line)

def debug_print(msg):
	"""
	Print a status message.
	"""
	print(decorate_line(msg))

