# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-B license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-B license and that you accept its terms.


from __future__ import absolute_import

import subprocess


try:
	# convert Py2 `raw_input` to `input` (Py3)
	input = raw_input
except NameError:
	pass


def _communicate(p, relay_input=False):
	if relay_input:
		return p.communicate(input())
	else:
		return p.communicate()


def with_subprocess(cmd, *args, **kwargs):
	"""
	Execute an external command.

	Arguments:

		cmd (str): (path to) command free of input arguments.
			Input arguments to `cmd` are provided separately
			as *\*args*.

		output (bool): return *stdout* command output (`str`) if *stderr* was silent, or
			otherwise *(stdout, stderr)* command output (`(str, str)`. (default: False)

		wait (bool): wait for completion but do not return anything. (default: False)

		error (bool or Exception): if *stderr* receives input, raise an error with
			*stderr* input as *__init__* argument. Default exception is `RuntimeError`.
			(default: False)

		input (bool): call `input` or `raw_input` and relay the user-supplied input to
			the command. (default: False)

	`input`, `output`, `wait` and `error` can be passed only as keyword arguments.

	The extra keyword arguments are passed to `subprocess.Popen`.

	Note that if you set `error` to ``True`` or any ``Exception``, `output` implicitly
	defaults to ``True``.
	You can prevent this behavior by explicitly passing ``output=False``.

	Similarly, if `output` is ``True``, errors are also caught and no longer appear on
	*stdout*.
	To prevent this, explicitly set `error` to ``False``.

	If ``stdout`` or ``stderr`` are set as extra keyword arguments, these explicit values
	prevail over those derived from the `output` and `error` arguments.

	See also https://docs.python.org/2.7/library/subprocess.html.
	"""
	cmd = (cmd,) + args
	return_output = kwargs.pop('output', None)
	wait_for_completion = kwargs.pop('wait', None)
	fail_on_error = kwargs.pop('error', None)
	relay_input = kwargs.pop('input', None)
	if relay_input and 'stdin' not in kwargs:
		kwargs['stdin'] = subprocess.PIPE
	if return_output or fail_on_error:
		if not (return_output is False or 'stdout' in kwargs):
			kwargs['stdout'] = subprocess.PIPE
		if not (fail_on_error is False or 'stderr' in kwargs):
			kwargs['stderr'] = subprocess.PIPE
		p = subprocess.Popen(cmd, **kwargs)
		out, err = _communicate(p, relay_input)
		if err:
			if fail_on_error:
				try:
					if not isinstance(fail_on_error(), Exception):
						raise TypeError
				except TypeError:
					fail_on_error = RuntimeError
				raise fail_on_error(err)
			return (out, err)
		else:
			return out
	else:
		p = subprocess.Popen(cmd, **kwargs)
		if wait_for_completion or relay_input:
			_communicate(p, relay_input)

