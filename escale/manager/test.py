# -*- coding: utf-8 -*-

# Copyright @ 2021, Institut Pasteur
#      Contributor: François Laurent

# This file is part of the Escale software available at
# "https://github.com/francoislaurent/escale" and is distributed under
# the terms of the CeCILL-C license as circulated at the following URL
# "http://www.cecill.info/licenses.en.html".

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL-C license and that you accept its terms.


from escale.base import *
from .manager import Manager
from ..base.config import storage_space_unit
from ..relay.info import Metadata, parse_metadata
from ..relay.index import AbstractIndexRelay
import os
import bz2
import time
import shutil
import tarfile
import tempfile
from collections import defaultdict
from random import shuffle


class IndexManager(Manager):

    def __init__(self, relay, *args, **kwargs):
        #if not isinstance(relay, AbstractIndexRelay):
        #    raise TypeError("relay is not an IndexRelay")
        max_page_size, max_page_size_unit = kwargs.pop('maxpagesize', (200, None))
        if max_page_size_unit:
            max_page_size = max_page_size * storage_space_unit[max_page_size_unit]# * 1048576
        try:
            upload_max_wait = kwargs['config']['upload max wait']
        except KeyError:
            upload_max_wait = 600
        Manager.__init__(self, relay, *args, **kwargs)
        self.priority = None
        try:
            priority = kwargs['priority'].lower()
        except KeyError:
            pass
        else:
            if priority == 'push':
                self.priority = 'upload'
            elif priority == 'pull':
                self.priority = 'download'
            elif priority in ('download', 'upload'):
                self.priority = priority
            else:
                self.logger.warning('unsupported value for `priority`: %s; ignoring', priority)
        self.pull_overwrite = kwargs.get('pulloverwrite', False)
        self.repository.unsafe = True
        self.max_page_size = max_page_size
        self.extraction_repository = tempfile.mkdtemp()
        self.upload_max_wait = upload_max_wait
        self.download_idle = True
        self.onetime_log = set()

    def terminate(self, pullers):
        return self.count is None or self.count <= len(pullers)

    def __del__(self):
        try:
            shutil.rmtree(self.extraction_repository)
        except AttributeError:
            # exception raised in __init__
            pass
        #Manager.__del__(self)

    def sanityChecks(self):
        self.relay.repairUpdates()
        Manager.sanityChecks(self)
        self.relay.clearIndex()

    def shuffle(self, _list, with_updates_first=False):
        if with_updates_first:
            with_, without_ = [], []
            for page in _list:
                if self.relay.hasUpdate(page):
                    with_.append(page)
                else:
                    without_.append(page)
            shuffle(with_)
            shuffle(without_)
            _list = with_ + without_
        else:
            shuffle(_list)
        return _list

    def download(self):
        return False

    def upload(self):
        new = False
        indexed = defaultdict(list)
        not_indexed = []
        for resource in self.localFiles():
            remote_file = resource
            if self.relay.indexed(remote_file):
                indexed[self.relay.page(remote_file)].append(resource)
            else:
                not_indexed.append(resource)
        local_file_count = {p: len(indexed[p]) for p in indexed}
        if 1 < self.verbosity:
            self.logger.debug('upload has listed %s local files', sum(local_file_count.values()))
        #
        t0 = None
        while True:
            any_page_update, any_postponed = False, False
            for page in indexed:
                #self.logger.debug("page '%s'", page)
                pushed = []
                fd, archive = tempfile.mkstemp()
                os.close(fd)
                tmpdir = tempfile.mkdtemp()
                try:
                    with self.relay.setUpdate(page) as update:
                        try:
                            page_index = self.relay.getPageIndex(page)
                        except MissingResource:
                            self.logger.error('missing page index')
                            self.relay.remoteListing()
                            update = {}
                            page_index = {}
                        if 0 < self.verbosity:
                            self.logger.debug("page '%s' has %s entries (locally: %s)",
                                page, len(page_index), len(indexed[page]))
                        size = 0
                        for n, resource in enumerate(indexed[page]):
                            remote_file = resource
                            local_file = self.repository.absolute(resource)
                            try:
                                checksum, last_modified = self.checksum(resource, return_mtime=True)
                            except OSError as e: # file unlinked since last call to localFiles?
                                self.logger.debug('%s', e)
                                continue
                            try:
                                page_metadata = parse_metadata(page_index[remote_file])
                            except KeyError:
                                pass
                            else:
                                if (self.timestamp or self.hash_function) and \
                                        not page_metadata.fileModified(local_file, last_modified, \
                                            checksum, remote=False, debug=self.logger.debug):
                                    continue
                            metadata = Metadata(target=remote_file, timestamp=last_modified, checksum=checksum, pusher=self.relay.client)
                            # add to the archive
                            new = True
                            dirname = os.path.dirname(resource)
                            if dirname:
                                dirname = '/'.join((tmpdir, dirname))
                            else:
                                dirname = tmpdir
                            if not os.path.exists(dirname):
                                os.makedirs(dirname)
                            local_copy = '/'.join((tmpdir, resource))
                            shutil.copy2(local_file, local_copy)
                            # add to the update index
                            update[remote_file] = metadata
                            pushed.append(remote_file)
                            # check the update data size
                            size += float(os.stat(local_copy).st_size) / 1048576.
                            if self.max_page_size < size:
                                if 1 < self.verbosity:
                                    self.logger.debug('the update cannot be larger (%s < %s)', \
                                        self.max_page_size, size)
                                break
                        if update:
                            with tarfile.open(archive, mode='w:bz2') as tar:
                                for f in os.listdir(tmpdir):
                                    tar.add('/'.join((tmpdir, f)), arcname=f, recursive=True)
                            final_file = self.encryption.encrypt(archive)
                            while True:
                                self.logger.info('cancelling update')
                                self.logger.debug('%s', update)
                                break
                                try:
                                    with self.tq_controller.push(archive):
                                        self.logger.debug("uploading update data for page '%s'", page)
                                        self.relay.setUpdateData(page, final_file)
                                except QuotaExceeded as e:
                                    self.logger.info("%s; no more files can be sent", e)
                                    if not self.tq_controller.wait():
                                        raise
                                else:
                                    break
                            self.encryption.finalize(final_file)
                        indexed[page] = indexed[page][n+1:]
                    any_page_update = bool(pushed)
                except PostponeRequest:
                    any_postponed = True
                    pushed = []
                    continue
                except: # new in 0.7.10
                    pushed = []
                    raise
                finally:
                    if pushed:
                        self.reportTransferred('upload', pushed)
                        #for resource in pushed:
                        #    self.logger.info("file '%s' successfully uploaded", resource)
                    shutil.rmtree(tmpdir)
                    os.unlink(archive)

            if self.mode == 'upload' or self.priority == 'upload':
                indexed = { page: files for page, files in indexed.items() if files }
                #self.logger.debug('%s page(s) and %s files remaining', len(indexed),
                #    0 if indexed else sum([ len(p) for p in indexed.values() ]))
                if not indexed:
                    break
            else:
                break

            if 0 < self.verbosity:
                # if the number of pending files len(indexed[p]) == local_file_count[p],
                # then an update was already available on the relay and no file have been checked
                pending_file_count = {}
                unexplored_pages = []
                for p in indexed:
                    _count = len(indexed[p])
                    if _count < local_file_count[p]:
                        pending_file_count[p] = _count
                    else:
                        unexplored_pages.append(p)
                if pending_file_count:
                    self.logger.debug('%s files of %s are still pending for upload in pages %s (respectively); staying in the upload phase',
                        '/'.join([str(pending_file_count[p]) for p in pending_file_count]),
                        '/'.join([str(local_file_count[p]) for p in pending_file_count]),
                        '/'.join(pending_file_count.keys()))
                if unexplored_pages:
                    if unexplored_pages[1:]:
                        self.logger.debug('pages %s are unexplored yet', quote_join(unexplored_pages, final=' and '))
                    else:
                        self.logger.debug('page %s is unexplored yet', unexplored_pages[0])
            if any_page_update:
                t0 = None
            elif any_postponed:
                #self.logger.debug('pending update(s) postponed')
                if t0 is None:
                    t0 = time.time()
                elif self.upload_max_wait is not None and \
                    self.upload_max_wait < time.time() - t0:
                    self.logger.debug('timeout %ss', int(time.time() - t0))
                    break
                if not self.tq_controller.wait():
                    self.logger.debug('timeout')
                    break
                #for page in indexed:
                #    self.relay.loaded(page)
                self.remoteListing()
        #
        if not_indexed:
            remote = self.relay.listTransferred('', end2end=False)
        for resource in not_indexed:
            remote_file = resource
            local_file = self.repository.absolute(resource)
            if PYTHON_VERSION == 2 and isinstance(remote_file, unicode) and \
                remote and isinstance(remote[0], str):
                remote_file = remote_file.encode('utf-8')
            exists = remote_file in remote
            checksum = self.checksum(resource)
            modified = False # if no remote copy, this is ignored
            if (self.timestamp or self.hash_function) and exists:
                # check file last modification time and checksum
                meta = self.relay.getMetadata(remote_file, timestamp_format=self.timestamp)
                if meta:
                    modified = meta.fileModified(local_file, checksum=checksum, remote=False, \
                        debug=self.logger.debug)
                else:
                    # no meta information available
                    modified = True
                    # this may not be true, but this will update the meta
                    # information with a valid content.
            if not exists or modified:
                new = True
                try:
                    last_modified, _ = self.checksum_cache[resource]
                except (TypeError, KeyError):
                    last_modified = os.path.getmtime(local_file)
                #temp_file = self.encryption.encrypt(local_file)
                self.logger.info("uploading file '%s'", remote_file)
                try:
                    with self.tq_controller.push(local_file):
                        ok = True
                #        ok = self.relay.push(temp_file, remote_file, blocking=False,
                #            last_modified=last_modified, checksum=checksum)
                except QuotaExceeded as e:
                    self.logger.info("%s; no more files can be sent", e)
                    ok = False
                #finally:
                #    self.encryption.finalize(temp_file)
                if ok:
                    self.logger.debug("file '%s' successfully uploaded", remote_file)
                elif ok is not None:
                    self.logger.warning("failed to upload '%s'", remote_file)
        return new

    def localFiles(self, path=None):
        ls = Manager.localFiles(self, path)
        repo = 'screens/tihana/t2' # adapt
        ext = 'outline' # adapt
        import subprocess
        ls_check = subprocess.run(f'find {repo} -type f -regex ".*[.]{ext}" -print',
                shell=True, capture_output=True) 
        ls_check = set(ls_check.stdout.decode('utf8').split())
        if not (ls_check - set(ls)):
            self.logger.error('files are missing in the local listing: \n' + '\n'.join(ls_check))
            raise AssertionError
        return ls

    def reportTransferred(self, download_or_upload, transferred_files):
        if transferred_files:
            self.logger.info('\n'.join(\
                    ['successfully {}ed files:'.format(download_or_upload)]+\
                    self._shorten(transferred_files)))

    def _shorten(self, filepaths, maxlen=70, prefixlen=20, suffixlen=40):
        msg = []
        filenames = defaultdict(list)
        for fp in filepaths:
            dirname, filename = os.path.split(fp)
            filenames[dirname].append((filename, fp))
        for dirname in filenames:
            fs = filenames[dirname]
            assert fs
            if fs[1:]:
                if maxlen < len(dirname)+3:
                    dirname = _shorten(dirname, prefixlen, suffixlen)
                msg.append("in '{}':".format(dirname))
                for f, _ in fs:
                    if maxlen < len(f)+3:
                        f = _shorten(f, prefixlen, suffixlen)
                    msg.append(" + '{}'".format(f))
            else:
                _, f = fs[0]
                if maxlen < len(f):
                    f = _shorten(f, prefixlen, suffixlen)
                #msg.append("'{}'".format(os.path.join(dirname, f)))
                msg.append("'{}'".format(f))
        return msg

def _shorten(name, prefixlen, suffixlen):
    if prefixlen is None:
        return '...'+name[-suffixlen:]
    elif suffixlen is None:
        return name[:prefixlen]+'...'
    else:
        return '...'.join((name[:prefixlen], name[-suffixlen:]))

