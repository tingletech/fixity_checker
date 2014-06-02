#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yet another fixity checker.
"""
import sys
import os
import argparse
from string import Template
from shove import Shove
from appdirs import user_cache_dir
from pprint import pprint as pp
import logging
from functools import partial
import hashlib

# ionice... http://stackoverflow.com/a/6245160/1763984
import psutil
p = psutil.Process(os.getpid())
if hasattr(p,'set_ionice'): # ... if we can http://stackoverflow.com/a/34472/1763984
    p.set_ionice(psutil.IOPRIO_CLASS_IDLE)


def main(argv=None):
    cache = "".join(['file://',user_cache_dir('yafixity', 'cdlib')])
    parser = argparse.ArgumentParser(description='checkfile')
    parser.add_argument('filename', nargs=1)
    parser.add_argument('--update', dest='update', action='store_true',
                        help='skip file check and update recorded observation')
    parser.add_argument('--cache_url',
                        help='database URL to shove to (file://... for files)',
                        default=cache)
    parser.add_argument('--hashlib', default='md5')
    parser.add_argument('--loglevel', default='ERROR')

    if argv is None:
        argv = parser.parse_args()

    # set debugging level
    numeric_level = getattr(logging, argv.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % argv.loglevel)
    logging.basicConfig(level=numeric_level, )
    logging.debug(argv)

    hasher = hashlib.new(argv.hashlib)
 
    filename = os.path.abspath(argv.filename[0])
    filename_key = hashlib.sha224(filename).hexdigest()
    logging.info('{0}'.format(filename))

    seen_now = analyze_file(filename, hasher)
    observations = Shove(argv.cache_url)

    if filename_key in observations and not argv.update:
        assert(compare_sightings(seen_now, observations[filename_key]))
    else:
        observations[filename_key] = seen_now
        observations.sync()


def compare_sightings(now, before):
    """ return False if sightings differ, otherwise True """
    if not now['size'] == before['size']:
        logging.error('sizes do not match')
        return False
    # we might not have used the same hasher before
    hashcheck = [x for x in now.keys() if x != 'size'][0] # TODO: loop this
    if hashcheck in before:
        if now[hashcheck] != before[hashcheck]:
            logging.error('checksums differ before:{1} now:{0}'.format(now[hashcheck], before[hashcheck]))
            return False
    else:
        logging.info('{0} not seen before for this'.format(hashcheck))
    return True


def analyze_file(filename, hasher):
    """ returns a dict of hash and size in bytes """
    # http://www.pythoncentral.io/hashing-files-with-python/
    BLOCKSIZE = 1024 * hasher.block_size
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
        # in the future, add os.POSIX_FADV_DONTNEED support 
        # http://www.gossamer-threads.com/lists/python/python/1063241
    return { 
      'size': os.path.getsize(filename),
      hasher.name : hasher.hexdigest()
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
