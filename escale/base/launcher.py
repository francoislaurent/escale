# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright @ 2021, Institut Pasteur
#   Contributor: François Laurent
#   Contributions: keep_alive from config, all PIDs are tracked

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import logging, logging.handlers
from multiprocessing import Process, Queue
import threading
import traceback

from .exceptions import *
from .essential import *
from .config import parse_cfg, default_section, global_fields
from escale.log import *
# separate imports instead of single escale.manager
# single import breaks Sphinx
from escale.manager.config import *
from escale.manager.manager import Manager
from escale.manager.index import IndexManager
from escale.manager.access import AccessController, access_modifier_prefix
from escale.manager.history import History, usage_statistics_prefix
from escale.manager.cache import checksum_cache_prefix
from escale.cli.controller import DirectController, UIController


def make_client(config, repository, log_handler=None, ui_connector=None):
    """
    Initialize an escale client.
    
    The client-specific logger and a manager are set.

    Arguments:

        config (ConfigParser): config object.

        repository (str): config section name.

        log_handler (any): passed to :meth:`addHandler` (see the `logging` module).

        ui_connector (tuple): arguments passed to :class:`UIController`.

    Returns:

        escale.manager.Manager or escale.manager.index.IndexManager: client manager.

    """
    # set logger
    logger = logging.getLogger(log_root).getChild(repository)
    logger.setLevel(logging.DEBUG)
    if log_handler is not None:
        logger.propagate = False
        if isinstance(log_handler, tuple):
                        log_handler = log_handler[0](*log_handler[1:])
        logger.addHandler(log_handler)
    # check arguments
    if repository in ['error']:
        msg = "'{}' is a reserved keyword; please set another name for your repository in '{}'".format(repository, config.filename)
        try:
            logger.critical(msg)
        except:
            pass
        raise ValueError(msg)
    # ui
    if ui_connector is None:
        ui_controller = DirectController(logger=logger)
    else:
        ui_controller = UIController(*ui_connector)
        ui_controller.logger = logger
    # parse config
    relay, args = parse_section(config, repository, logger)
    # local repository
    path = args.pop('path', None)
    mode = args.pop('mode', None)
    lr_controller = AccessController(repository, path=path, mode=mode,
            persistent=get_cache_file(config, repository,
                prefix=access_modifier_prefix),
            ui_controller=ui_controller, **args)
    # time and quota control
    refresh = args.pop('refresh', True)
    quota = args.pop('quota', None)
    tq_controller = History(refresh=refresh, quota=quota, logger=logger,
            repository=repository,
            persistent=get_cache_file(config, repository,
                prefix=usage_statistics_prefix))
    # checksum cache
    checksum_cache = args.pop('checksumcache', True)
    if isinstance(checksum_cache, bool) and checksum_cache:
        checksum_cache = get_cache_file(config, repository,
                prefix=checksum_cache_prefix)
    # extra UI options
    ui_controller.maintainer = args.pop('maintainer', None)
    # ready
    index = args.pop('index', False)
    if index:
        Mngr = IndexManager
    else:
        Mngr = Manager
    manager = Mngr(relay,
            repository=lr_controller,
            ui_controller=ui_controller,
            tq_controller=tq_controller,
            checksum_cache=checksum_cache,
            **args)
    return manager


def escale(config, repository, log_handler=None, ui_connector=None):
    """
    Read the section related to a repository in a loaded configuration object and runs a 
    :class:`~escale.manager.Manager` for that repository.

    Arguments:

        config (ConfigParser): configuration object.

        repository (str): configuration section name or, alternatively, client name.

        log_handler (log handler): input argument to :meth:`~logging.Logger.addHandler`.

        ui_connector (any): connector to user-interface controller.
    """
    manager = make_client(config, repository, log_handler=log_handler, ui_connector=ui_connector)
    try:
        result = manager.run()
    #except ExpressInterrupt:
    #    raise
    except Exception as exc:
        if not manager.ui_controller.failure(repository, exc, traceback.format_exc()):
            raise exc
    else:
        manager.ui_controller.success(repository, result)



def escale_launcher(cfg_file, msgs=[], verbosity=logging.NOTSET, keep_alive=None):
    """
    Parse a configuration file, set the logger and launch the clients in separate subprocesses.

    Arguments:

        cfg_file (str): path to a configuration file.

        msgs (list): list of pending messages (`str` or `tuple`).

        verbosity (bool or int): verbosity level.

        keep_alive (bool or int): if ``True`` or non-negative `int`, clients are ran again 
            after they hit an unrecoverable error; 
            multiple threads and subprocesses are started even if a single client is defined;
            if `int`, specifies default sleep time after a subprocess crashed.

    """
    # parse the config file
    config, cfg_file, msgs = parse_cfg(cfg_file, msgs)
    # configure logger
    logger, msgs = set_logger(config, cfg_file, verbosity, msgs)
    # flush messages
    flush_init_messages(logger, msgs)
    # parse keep_alive
    restart_delay = 0
    if keep_alive is None:
        # read from config
        global_config = parse_fields(config, default_section, global_fields, logger)
        keep_alive = global_config.get('keepalive', False)
    # `in` may coerce bools to ints
    if keep_alive not in [False, True] and isinstance(keep_alive, (int, float)):
        restart_delay = keep_alive
        keep_alive = True
    #logger.debug('keep_alive= %s', keep_alive)
    #logger.debug('restart_delay= %s', restart_delay)
    # wrap Process.start
    pidfile = get_pid_file(config)
    def startWorker(worker):
        worker.start()
        if os.path.isfile(pidfile):
            with open(pidfile, 'a') as f:
                f.write('\n'+str(worker.pid))
        else:
            with open(pidfile, 'w') as f:
                f.write(str(worker.pid))
    # launch each client
    sections = config.sections()
    if sections[1:] or keep_alive: # if multiple sections
        if PYTHON_VERSION == 3:
            log_queue = Queue()
            log_listener = QueueListener(log_queue)
            log_handler = (logging.handlers.QueueHandler, log_queue)
        elif PYTHON_VERSION == 2:
            import escale.log.socket as socket
            log_host = 'localhost'
            log_listener = socket.SocketListener(log_host)
            log_handler = (logging.handlers.SocketHandler, log_host, log_listener.port)
        # logger
        logger_thread = threading.Thread(target=log_listener.listen)
        logger_thread.start()
        # result handling
        result_queue = Queue()
        # user interface
        ui_controller = UIController(logger=logger, parent=result_queue)
        ui_thread = threading.Thread(target=ui_controller.listen)
        ui_thread.start()
        # escale subprocesses
        workers = {}
        for section in config.sections():
            worker = Process(target=escale,
                name='{}.{}'.format(log_root, section),
                args=(config, section, log_handler, ui_controller.conn))
            workers[section] = worker
            startWorker(worker)
        # wait for everyone to terminate
        result_type = Exception if keep_alive else RestartRequest
        try:
            if keep_alive:
                active_workers = len(workers)
                while 0 < active_workers:
                    #logger.debug('waiting for a process to return')
                    section, result = result_queue.get()
                    #logger.debug('%s', result)
                    if (isinstance(result, type) and issubclass(result, result_type)) \
                            or isinstance(result, result_type):
                        workers[section].join() # should have already returned
                        # restart worker
                        worker = Process(target=escale,
                            name='{}.{}'.format(log_root, section),
                            args=(config, section, log_handler,
                                ui_controller.conn))
                        workers[section] = worker
                        ui_controller.restartWorker(section, restart_delay)
                        startWorker(worker)
                    else:
                        active_workers -= 1
            else:
                for worker in workers.values():
                    worker.join()
        except ExpressInterrupt as exc:
            logger.debug('%s', type(exc).__name__)
            for section, worker in workers.items():
                try:
                    worker.terminate()
                except ExpressInterrupt as exc:
                    logger.debug('%s', type(exc).__name__)
                    raise
                except Exception as e:
                    # 'NoneType' object has no attribute 'terminate'
                    logger.warning("[%s]: %s", section, e)
                    logger.debug("%s", workers)
            for worker in workers.values():
                try:
                    worker.join(1)
                except ExpressInterrupt as exc:
                    logger.debug('%s', type(exc).__name__)
                    raise
                except:
                    pass
        except:
            logger.debug('%s', traceback.print_exc())
            raise
        ui_controller.abort()
        log_listener.abort()
        ui_thread.join(1)
        logger_thread.join(1)
    else:
        try:
            escale(config, sections[0])
        except ExpressInterrupt as exc:
            logger.debug('%s', type(exc).__name__)
            raise
    logger.debug('exiting')


