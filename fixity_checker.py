#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yet another fixity checker.
"""
import sys
import os
import argparse
from shove import Shove
from appdirs import user_data_dir
import logging
import hashlib
import psutil


def main(argv=None):
    data = "".join(['file://', user_data_dir('yafixity', 'cdlib')])
    parser = argparse.ArgumentParser(description='Yet another fixity checker')
    parser.add_argument('filepath', nargs='+', help='file or directory')
    parser.add_argument('--update', dest='update', action='store_true',
                        help='skip file check and update observations')
    parser.add_argument('--data_url',
                        help='database URL to shove to (file://... for files)',
                        default=data)
    parser.add_argument('--hashlib', default='sha512')
    parser.add_argument('--loglevel', default='ERROR')

    if argv is None:
        argv = parser.parse_args()

    # set debugging level
    numeric_level = getattr(logging, argv.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % argv.loglevel)
    logging.basicConfig(level=numeric_level, )
    logging.debug(argv)

    # ionice... http://stackoverflow.com/a/6245160/1763984
    p = psutil.Process(os.getpid())
    # ... if we can http://stackoverflow.com/a/34472/1763984
    if hasattr(p, 'set_ionice'):
        p.set_ionice(psutil.IOPRIO_CLASS_IDLE)

    # persisted dict interface for long term memory
    observations = Shove(argv.data_url)

    for filepath in argv.filepath:
        assert filepath != '', "arguments can't be empty"
        check_one_arg(filepath, observations, argv.hashlib, argv.update)

    observations.close()

    return True


def check_one_arg(filein, observations, hash, update):
    """check if the arg is a file or directory, walk directory for files"""
    if os.path.isdir(filein):
        for root, ____, files in os.walk(filein):
            for f in files:
                fullpath = os.path.join(root, f)
                check_one_file(fullpath, observations, hash, update)
    else:
        check_one_file(filein, observations, hash, update)


def check_one_file(filein, observations, hash, update):
    """check file one file against our memories"""
    # normalize filename, take hash for key
    filename = os.path.abspath(filein)
    filename_key = hashlib.sha224(filename.encode('utf-8')).hexdigest()
    logging.info('{0} {1}'.format(filename, filename_key))

    seen_now = analyze_file(filename, hash)
    logging.debug(seen_now)

    if filename_key in observations and not update:
        # make sure things match
        news = {}
        looks_the_same = compare_sightings(
            seen_now, observations[filename_key], news
        )
        assert bool(looks_the_same), "%r has changed" % filename
        if any(news):
            update = observations[filename_key]
            update.update(news)
            observations[filename_key] = update
            observations.sync()
            logging.debug('new memory')
            logging.debug(update)
    else:
        # update observations
        observations[filename_key] = seen_now
        observations.sync()
        logging.info('update observations')


def compare_sightings(now, before, news={}):
    """ return False if sightings differ, otherwise True """
    logging.debug('now')
    logging.debug(now)
    logging.debug('before')
    logging.debug(before)
    if not now['size'] == before['size']:
        logging.error('sizes do not match')
        return False
    for check in now.keys():
        if check in before:
            if now[check] != before[check]:
                logging.error('{2} differ before:{1} now:{0}'.format(
                    now[check], before[check], check)
                )
                return False
        else:
            logging.info('{0} not seen before for this'.format(check))
            news[check] = now[check]
    return True


def analyze_file(filename, hash):
    """ returns a dict of hash and size in bytes """
    # http://www.pythoncentral.io/hashing-files-with-python/
    hasher = hashlib.new(hash)
    BLOCKSIZE = 1024 * hasher.block_size
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
        # in the future, add os.POSIX_FADV_DONTNEED support
        # needs python 3 and newer linux kernel
        # http://www.gossamer-threads.com/lists/python/python/1063241
    return {
        'size': os.path.getsize(filename),
        hasher.name: hasher.hexdigest(),
        'path': filename
    }


# main() idiom for importing into REPL for debugging
if __name__ == "__main__":
    sys.exit(main())


"""
Copyright © 2014, Regents of the University of California
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
- Neither the name of the University of California nor the names of its
  contributors may be used to endorse or promote products derived from this
  software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
