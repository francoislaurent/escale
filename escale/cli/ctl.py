# -*- coding: utf-8 -*-

# Copyright © 2017, François Laurent

# Copyright © 2018, Institut Pasteur
#    Contributor: François Laurent
#    Contribution: migrate can operate cross-section with a single configuration

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


import sys
import os
import traceback
import time
from math import *

from escale import *
from escale.base.essential import *
from escale.base.config import *
from escale.relay.info import *
from escale.manager.access import *
from escale.base.launcher import *
from escale.manager.migration import *
from escale.manager.backup import *
from escale.relay.index import *

import tarfile
import shutil
import subprocess # escale.manager.migration mysteriously overwrites subprocess, therefore subprocess should imported after
from collections import defaultdict


def start(pidfile=None):
    """
    Start all the client defined in the default configuration file.

    This routine is the only one that records the pid of the main process in file.
    """
    if not pidfile:
        pidfile = get_pid_file()
    if os.path.exists(pidfile):
        print("{} is already running; if not, delete the '{}' file".format(PROGRAM_NAME, pidfile))
        return 1
    try:
        raise ImportError # daemon.DaemonContext does not seem to work (at least in Python 2.7)
        import daemon
        import daemon.pidfile
    except ImportError:
        python = sys.executable
        if python is None:
            if PYTHON_VERSION == 3 and not ispc():
                python = 'python3'
            else:
                python = 'python'
        kwargs = {}
        if ispc():
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        sub = subprocess.Popen([python, '-m', PROGRAM_NAME], **kwargs) #, '-r'
        with open(pidfile, 'w') as f:
            f.write(str(sub.pid))
    else:
        with daemon.DaemonContext(working_directory=os.getcwd(),
                pidfile=daemon.pidfile.TimeoutPIDLockFile(pidfile)):
            escale_launcher()
    return 0


def stop(pidfile=None):
    """
    Kill all the running escale processes.
    """
    if not pidfile:
        pidfile = get_pid_file()
    if not os.path.exists(pidfile):
        print("{} is not running".format(PROGRAM_NAME))
        return 1
    with open(pidfile, 'r') as f:
        pid = str(f.read())
    if ispc():
        if PYTHON_VERSION == 3:
            import signal
            try:
                os.kill(int(pid), signal.CTRL_C_EVENT)
            except OSError as exc:
                if exc.args and exc.args[0] == 22:
                    print("{} is not running".format(PROGRAM_NAME))
                    return 1
        else:
            kill = ['taskkill', '/t', '/f', '/pid']
            #p = subprocess.Popen(['tasklist'], stdout=subprocess.PIPE)
            subprocess.call(kill+[pid])
            #os.unlink(pidfile)
            #subprocess.call(['taskkill', '/f', '/im', 'python.exe']) # self-kill
        os.unlink(pidfile)
    else:
        kill = ['kill']
        p = subprocess.Popen(['ps', '-eo', 'ppid,pid'], stdout=subprocess.PIPE)
        ps = p.communicate()[0]
        children = []
        for line in ps.splitlines():
            line = asstr(line)
            ppid, cpid = line.split()
            if ppid == pid:
                children.append(cpid)
        if not children:
            print('no {} subprocesses found'.format(PROGRAM_NAME))
        for child in children:
            subprocess.call(kill+[child])
        subprocess.call(kill+[pid])
        # no need for the code block below with 3.6.8 and 3.7.3
        #if PYTHON_VERSION == 3: # repeat
        #    time.sleep(1)
        #    subprocess.call(kill+[pid])
    os.unlink(pidfile)


def restart(pidfile=None):
    """
    Restart all the running escale processes.
    """
    stop(pidfile)
    time.sleep(1)
    return start(pidfile)


def access(modifiers=None, resource=None, repository=None):
    """
    Get or set access modifiers of a resource.
    """
    get_modifiers = modifiers is None
    set_modifiers = modifiers is not None
    if resource and os.path.exists(resource):
        if not os.path.isabs(resource):
            resource = join(os.getcwd(), resource)
    cfg, _, _ = parse_cfg()
    if repository is None:
        repositories = cfg.sections()
    elif isinstance(repository, (list, tuple)):
        repositories = repository
    else:
        repositories = [repository]
    mmap1 = {'?': None, '+': True, '-': False}
    mmap2 = { mmap1[k]: k for k in mmap1 }
    ok = False
    for rep in repositories:
        args = parse_fields(cfg, rep, fields)
        persistent = get_cache_file(config=cfg, section=rep, prefix=access_modifier_prefix)
        if get_modifiers and not os.path.exists(persistent):
            continue
        ctl = AccessController(rep, persistent=persistent, create=set_modifiers, **args)
        if set_modifiers:
            assert ctl.persistent
            set = dict(r=ctl.setReadability, w=ctl.setWritability)
            for mode in set:
                if mode in modifiers:
                    i = modifiers.index(mode) + 1
                    try:
                        p = modifiers[i]
                    except IndexError:
                        p = True
                    else:
                        p = mmap1[p]
                    try:
                        set[mode](resource, p)
                    except OSError as e:
                        #print(e)
                        pass
                    else:
                        ok = True
        if get_modifiers:
            try:
                modifiers = 'r{}w{}'.format(mmap2[ctl.getReadability(resource)],
                        mmap2[ctl.getWritability(resource)])
            except Exception as e:
                #print(e) # TODO: identify which exception
                pass
            else:
                ok = not ok
                if not ok:
                    break
    if ok:
        if get_modifiers:
            return modifiers
    else:
        if set_modifiers or not modifiers:
            raise OSError("cannot find file '{}'".format(resource))
        elif get_modifiers:
            raise ValueError("'{}' found in multiple repositories".format(resource))


def migrate(repository=None, destination=None, fast=None):
    """
    Migrate a relay repository from a host to another.

    Supports change in protocol and prefixes/suffixes of special files.
    """
    kwargs = {}
    if fast:
        kwargs['safe'] = False
    if os.path.isfile(destination):
        changes = parse_cfg(destination)
        repositories = changes.sections()
        if repository:
            if repository in repositories:
                for r in repositories:
                    if r != repository:
                        changes.remove_section(r)
            else:
                raise ValueError('cannot change repository name')
    else:
        config, cfg_file, msgs = parse_cfg()
        if repository:
            if repository not in config.sections():
                raise ValueError('cannot find repository: {}'.format(repository))
        else:
            repository = config.sections()
            if repository[1:]:
                raise ValueError("several repositories defined; please specify with '--repository'")
            repository = repository[0]
        kwargs['config'] = config
        if destination in config.sections():
            # new in 0.7.8
            logger, msgs = set_logger(config, cfg_file, msgs=msgs)
            flush_init_messages(logger, msgs)
            repository_logger = logger.getChild(repository)
            import logging
            repository_logger.setLevel(logging.DEBUG)
            migrate_repository(repository, config, alt_repo=destination, logger=repository_logger, **kwargs)
            return
        protocol, address, port, path = parse_address(destination)
        if not protocol:
            raise ValueError('relay host address should include protocol')
        changes = ConfigParser()
        changes.add_section(repository)
        changes.set(repository, default_option('protocol'), protocol)
        if address:
            changes.set(repository, default_option('address'), address)
        if port:
            changes.set(repository, default_option('port'), port)
        if path:
            changes.set(repository, default_option('dir'), path)
    migrate_repositories_and_update_config(changes, **kwargs)


def backup(repository=None, archive=None, fast=None):
    """
    Store a full relay repository in an archive.
    """
    kwargs = {}
    if fast:
        kwargs['safe'] = False
    backup_manager(archive, repository, 'backup', **kwargs)


def restore(repository=None, archive=None, fast=None):
    """
    Overwrite a relay repository with the uncompressed content of an archive.
    """
    kwargs = {}
    if fast:
        kwargs['safe'] = False
    backup_manager(archive, repository, 'restore', **kwargs)


def recover(repository=None, timestamp=None, overwrite=True, update=None, fast=None, page=None):
    """
    Make a relay repository with placeholder files or indices as if the local repository
    resulted from a complete download of an existing repository with escale.
    """
    if update is not None:
        overwrite = not update
    if timestamp:
        tsformat = timestamp
    else:
        tsformat = '%y%m%d_%H%M%S'
    if page:
        if isinstance(page, (tuple, list, frozenset, set)):
            page = list(page)
        else:
            page = [page]
        print('recovering page{}: {}'.format('s' if page[1:] else '', str(page)[1:-1]))
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        repositories = [ repository ]
    else:
        repositories = cfg.sections()
    fd, local_placeholder = tempfile.mkstemp()
    os.close(fd)
    try:
        for repository in repositories:
            client = make_client(cfg, repository)
            ls = client.localFiles()
            client.relay.open()
            try:
                # index relays.
                if fast:
                    client.remoteListing()
                    # call to `remoteListing` is not necessary otherwise
                    # thanks to `acquirePageLock` invocation
                if isinstance(client.relay, IndexRelay):
                    tmp = local_placeholder # just a temporary file
                    nfiles = len(ls)
                    index = {}
                    for n, resource in enumerate(ls):
                        local_file = client.repository.absolute(resource)
                        _page = client.relay.page(resource)
                        if page and _page not in page:
                            continue
                        #mtime = int(os.path.getmtime(local_file))
                        client.checksum(resource)
                        mtime, checksum = client.checksum_cache[resource]
                        metadata = Metadata(target=resource, timestamp=mtime,
                                checksum=checksum, pusher=client.relay.client)
                        if _page not in index:
                            index[_page] = {}
                        index[_page][resource] = metadata
                        if nfiles < 1000 or n % 20 == 19:
                            print('progress: {} of {} files'.format(n + 1, nfiles))
                    for _page in index:
                        if fast or client.relay.acquirePageLock(_page, 'w'):
                            try:
                                # this ignores `overwrite` (considers it as True)
                                client.relay.setPageIndex(_page, index[_page])
                            finally:
                                if not fast:
                                    client.relay.releasePageLock(_page)
                    continue
                # standard (no index) relays
                if fast:
                    client.logger.info('{} local files found'.format(len(ls)))
                    remote = client.relay.listTransfered()
                    client.logger.info('{} remote files found'.format(len(remote)))
                    ls = [ l for l in ls if l not in remote ]
                N = len(ls)
                client.logger.info('%s placeholder files to update', N)
                clock = time.time()
                progr = 0
                N = float(N)
                n = 0.0
                for remote in ls:
                    n += 1.0
                    local = client.repository.absolute(remote)
                    remote_placeholder = client.relay.placeholder(remote)
                    if not fast and client.relay.hasPlaceholder(remote):
                        if overwrite:
                            client.relay.unlink(remote_placeholder)
                        else:
                            continue
                    checksum = None
                    if client.hash_function:
                        timestamp = os.path.getmtime(local)
                        content = client.encryption.encrypt(local)
                        try:
                            with open(content, 'rb') as f:
                                checksum = client.hash_function(f.read())
                        finally:
                            client.encryption.finalize(content)
                    if checksum:
                        metadata = repr(Metadata(pusher=client.relay.client,
                                target=remote, timestamp=timestamp,
                                checksum=checksum))
                    else:
                        # old format
                        timestamp = time.strftime(tsformat,
                                time.gmtime(os.path.getmtime(local)))
                        metadata = timestamp
                    with open(local_placeholder, 'w') as f:
                        f.write(metadata)
                    client.relay._push(local_placeholder, remote_placeholder)
                    new_progr = int(floor(n / N * 100.0))
                    new_clock = time.time()
                    if progr < new_progr and 5 < new_clock - clock:
                        progr = new_progr
                        clock = new_clock
                        client.logger.info('progress: {}%'.format(progr))
            except:
                print(traceback.format_exc())
            finally:
                client.relay.close()
    finally:
        os.unlink(local_placeholder)


def rebase(repository=None, extra_path=None):
    """
    Update the existing indices so that the former repository is a sub-directory of the new repository.
    """
    if not extra_path:
        return
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if not repository:
        repository = cfg.sections()
        if repository[1:]:
            raise ValueError("several repositories defined; please specify with '--repository'")
        repository = repository[0]
    extra_path = os.path.expanduser(extra_path)
    dirname = os.path.dirname(extra_path)
    while True:
        first_dir = os.path.dirname(dirname)
        if first_dir == dirname:
            break
        dirname = first_dir
    client = make_client(cfg, repository)
    if isinstance(client.relay, TopDirectoriesIndex):
        raise NotImplementedError('cannot add upper directories with directory-based indexing')
    client.relay.open()
    client.remoteListing()
    fd, tmp = tempfile.mkstemp()
    try:
        os.close(fd)
        for page in client.relay.listPages():
            if client.relay.acquirePageLock(page, 'w'):
                try:
                    # persistent index
                    ix = client.relay.getPageIndex(page)
                    if ix:
                        ix = { join(extra_path, key): value for key, value in ix.items() }
                        client.relay.setPageIndex(page, ix)
                        if client.relay.hasUpdate(page):
                            # update index
                            ix = client.relay.getUpdateIndex(page, sync=False)
                            ix = { join(extra_path, key): value for key, value in ix.items() }
                            client.relay.setUpdateIndex(page, ix, sync=False)
                            # update data
                            encrypted = client.encryption.prepare(tmp)
                            client.relay.getUpdateData(page, encrypted)
                            client.encryption.decrypt(encrypted, tmp)
                            extraction_repository = tempfile.mkdtemp()
                            try:
                                os.makedirs(join(extraction_repository, extra_path))
                                with tarfile.open(tmp, mode='r:bz2') as tar:
                                    tar.extractall(join(extraction_repository, extra_path))
                                os.unlink(tmp)
                                with tarfile.open(tmp, mode='w:bz2') as tar:
                                    tar.add(join(extraction_repository, first_dir), arcname=first_dir,
                                            recursive=True)
                                encrypted = client.encryption.encrypt(tmp)
                                client.relay.setUpdateData(page, encrypted)
                                client.encryption.finalize(encrypted)
                            finally:
                                shutil.rmtree(extraction_repository)
                finally:
                    client.relay.releasePageLock(page)
    finally:
        os.unlink(tmp)
        client.relay.close()


def suspend(repository=None, page=None):
    """
    Lock pages so that the regular clients cannot push or pull.

    This procedure is designed for index-based repositories only.

    If a page to be locked is already locked, escalectl waits for the lock to be released.
    """
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        if isinstance(repository, (tuple, list)):
            repositories = repository
        else:
            repositories = [ repository ]
    else:
        repositories = cfg.sections()
    if page and not isinstance(page, (tuple, list)):
        page = [ page ]
    for repository in repositories:
        client = make_client(cfg, repository)
        if not isinstance(client.relay, IndexRelay):
            continue
        client.relay.client += '-suspend'
        client.relay.open()
        try:
            client.remoteListing()
            if page:
                unlocked = list(page)
            else:
                unlocked = client.relay.listPages()
            while unlocked:
                client.remoteListing()
                _unlocked = []
                for p in unlocked:
                    if not client.relay.hasLock(p) and \
                        client.relay.tryAcquirePageLock(p, 'w'):
                        print("in {}: page '{}' locked".format(repository, p))
                    else:
                        _unlocked.append(p)
                unlocked = _unlocked
        finally:
            client.relay.close()


def resume(repository=None, page=None):
    """
    Release locks set by the *suspend* procedure.
    """
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        if isinstance(repository, (tuple, list)):
            repositories = repository
        else:
            repositories = [ repository ]
    else:
        repositories = cfg.sections()
    if page and not isinstance(page, (tuple, list)):
        page = [ page ]
    for repository in repositories:
        client = make_client(cfg, repository)
        if not isinstance(client.relay, IndexRelay):
            continue
        client.relay.client += '-suspend'
        client.relay.open()
        try:
            client.remoteListing()
            if page:
                pages = list(page)
            else:
                pages = client.relay.listPages()
            for p in pages:
                if client.relay.hasLock(p):
                    try:
                        client.relay.releasePageLock(p)
                    except:
                        pass
                    else:
                        print("in {}: page '{}' unlocked".format(repository, p))
                else:
                    print("in {}: page '{}' locked by another client".format(repository, p))
        finally:
            client.relay.close()


def make_cache(repository=None, prefix='cc'):
    """
    Build the checksum cache.
    """
    if prefix != 'cc':
        raise NotImplementedError("'%s' not supported yet", prefix)
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        if isinstance(repository, (tuple, list)):
            repositories = repository
        else:
            repositories = [ repository ]
    else:
        repositories = cfg.sections()
    for repository in repositories:
        client = make_client(cfg, repository)
        if hasattr(client, 'checksum_cache_file') and client.checksum_cache_file:
            client.mode = 'upload'
            ls = client.localFiles()
            nfiles = len(ls)
            if 1000 < nfiles:
                step = int(10 * (round(log10(nfiles)) - 1))
            else:
                step = None
            try:
                for n, resource in enumerate(ls):
                    client.checksum(resource)
                    if step and n % step == step - 1:
                        print('progress: {} of {} files'.format(n + 1, nfiles))
            finally:
                print("writing cache for repository '{}'".format(repository))
                del client # writes down checksum cache file


def clear_cache(repository=None, prefix='cc'):
    """
    Remove caches.
    """
    if prefix != 'cc':
        raise NotImplementedError("'%s' not supported yet", prefix)
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        if isinstance(repository, (tuple, list)):
            repositories = repository
        else:
            repositories = [ repository ]
    else:
        repositories = cfg.sections()
    for repository in repositories:
        client = make_client(cfg, repository)
        try:
            os.unlink(client.checksum_cache_file)
        except ExpressInterrupt:
            raise
        except:
            pass

def list_pending(repository=None, page=None, fast=True, directories=False):
    """
    List the local files that are pending for upload.
    """
    if not fast:
        raise NotImplementedError('only fast mode is supported (only missing files are listed)')
    cfg, cfg_file, msgs = parse_cfg()
    logger, msgs = set_logger(cfg, cfg_file, msgs=msgs)
    flush_init_messages(logger, msgs)
    if repository:
        if isinstance(repository, (tuple, list)):
            repositories = repository
        else:
            repositories = [ repository ]
    else:
        repositories = cfg.sections()
    if page and not isinstance(page, (tuple, list)):
        page = [ page ]
    for repository in repositories:
        client = make_client(cfg, repository)
        if client.mode == 'download':
            continue
        if not isinstance(client.relay, IndexRelay):
            print('skipping repository: {}'.format(repository))
            continue
        indexed = defaultdict(list)
        not_indexed = []
        client.relay.open()
        try:
            for resource in client.localFiles():
                if client.relay.indexed(resource):
                    indexed[client.relay.page(resource)].append(resource)
                else:
                    not_indexed.append(resource)
            if page:
                pages = list(page)
            else:
                pages = indexed.keys()
            client.remoteListing()
            for p in pages:
                if p not in indexed:
                    continue
                page_index = client.relay.getPageIndex(p)
                if not page_index:
                    continue
                pending = set(indexed[p]) - set(list(page_index.keys()))
                if pending:
                    print("in page '{}':".format(p))
                    if directories:
                        for d in set([ os.path.dirname(f) for f in pending ]):
                            print(d)
                    else:
                        for f in pending:
                            print(f)
        finally:
            client.relay.close()

