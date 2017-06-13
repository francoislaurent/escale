# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from .format import *
from .config import *
from .auth import *
from .controller import *

__all__ = ['quote_join', 'debug_print', 'multiline_print', 'decorate_line',
		'edit_config', 'query_local_repository', 'query_relay_address',
		'request_credential', 'DirectController', 'UIController']

