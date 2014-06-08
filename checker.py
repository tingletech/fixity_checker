#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yet another fixity checker
server daemon
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import daemonocle
import argparse
import pkg_resources  # part of setuptools
from appdirs import user_data_dir
import sys
import os
import json
from pprint import pprint as pp
import time
from collections import namedtuple
import logging
from shove import Shove
import hashlib
import psutil

# raw_import() in 2 -> import() in 3
try:
    input = raw_input
except NameError:
    pass

# use readline if it is available for interactive input in init
try:
    import readline   # noqa
except NameError:
    pass

# ⏣ ⏣ ⏣ ⏣
APP_NAME = 'fixity_checker'
# ⏣ ⏣ ⏣ ⏣
# default directory for program files
try:
    CHECKER_DIR = os.environ['CHECKER_DIR']
except KeyError:
    CHECKER_DIR = user_data_dir(APP_NAME, 'cdlib')

# read version out of setup.py
__version__ = pkg_resources.require(APP_NAME)[0].version


def main(argv=None):
    """main: argument parsing and daemon setup"""
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='subparser_name')

    # **
    # ** list all subcommands and what they do
    # **

    commands = [
        ('init', 'runs and interactive script to configure a checker server'),
        ('show_conf', 'validate and show configuration options'),
        ('start', 'starts the checker server'),
        ('stop', 'stops the checker server'),
        ('status', 'produces a report of the server status and any errors'),
        ('restart', 'stop follow by a start'),
        ('update', 'updates fixity info (server must be stopped)'),
        ('json_report', 'json serialization of application data'),
        ('json_load', 'load json serialization into application data'),
    ]

    # **
    # ** set up parsers for the subcommands
    # **

    parsers = {}
    thismodule = sys.modules[__name__]

    for command, help in commands:
        parsers[command] = subparsers.add_parser(command,
                                                 help=help,
                                                 description=help)
        # map sub command to the function named _command_ in this file
        parsers[command].set_defaults(func=getattr(thismodule, command))

    # some subcommands need custom arguments
    parsers['start'].add_argument('--no-detach', dest='detach', action='store_false')
    parsers['update'].add_argument('file', nargs='+', help='file(s) to update')
    parsers['json_report'].add_argument('report_directory', nargs=1)
    parsers['json_load'].add_argument('report_directory', nargs=1)
    parsers['init'].add_argument('--non_interactive', nargs='+',
                                 dest='asset_directory',
                                 help='directories to check')

    # add CHECKER_DIR config_dir to the end of each parser
    # will show up at bottom of the help this way
    for command, ____ in commands:
        parsers[command].add_argument('-d', dest='config_dir',
                                      default=CHECKER_DIR,
                                      help='configuration directory')
    # **
    # ** parser the arguments and dispatch to correct function
    # **

    if argv is None:
        argv = parser.parse_args()

    # need to init before there is a conf to parse
    if sys.argv[1] == 'init':
        return init(argv)

    conf = _parse_conf(argv)

    def main_loop():
        # nested here to gain access to `conf`

        log_nice(conf)
        logging.info('Daemon is starting')
        while True:
            logging.debug('Still running')
            checker(conf)

    detach = True
    if 'detach' in argv:
        detach = argv.detach
    daemon = daemonocle.Daemon(
        worker=main_loop,
        shutdown_callback=cb_shutdown,
        pidfile=conf.daemon.pid,
        detach=detach
    )
    if sys.argv[1] in ['start', 'stop', 'restart']:
        daemon.do_action(sys.argv[1])
    else:
        return argv.func(conf, daemon)


def cb_shutdown(message, code):
    logging.info('Daemon is stopping')
    logging.debug(message)


def checker(conf):
    """ the main loop """
    MIN_LOOP = 15
    startLoopTime = time.time()
    # persisted dict interface for long term memory
    observations = Shove(conf.data['data_url'], protocol=2)

    # counts

    # for each hash type
    for hashtype in conf.data['hashlib']:
        logging.info('starting {0} checks'.format(hashtype))
        # for each command line argument
        for filepath in conf.data['archive_directories']:
            assert filepath, "arguments can't be empty"
            filepath = filepath+''  # http://fomori.org/blog/?p=486

            check_one_arg(filepath, observations, hashtype, False)

    # check for missing files
    logging.info('looking for missing files')
    for ____, value in list(observations.items()):
        assert os.path.isfile(value['path']),\
            "{} no longer exists or is not a file".format(value['path'])

    observations.close()

    # output json reports
    elapsedLoopTime = time.time() - startLoopTime
    logging.info("elapsedLoopTime {0} {1} files {2} bytes".format(elapsedLoopTime))

    if elapsedLoopTime < MIN_LOOP:
        nap = MIN_LOOP - elapsedLoopTime
        logging.info('sleeping for {0}'.format(nap))
        time.sleep(nap)


# ⌦
# ⌦  following functions impliment subcommands
# ⌦


def init(args):
    """ setup wizard """
    conf = args.config_dir

    # don't run more than once
    assert not(os.path.exists(conf)), \
        "{} directory specified for init must not exist".format(conf)

    data_url_default = 'file://{}/'.format(os.path.abspath(
                                           os.path.join(conf,
                                                        'fixity_data_raw')))

    # if there are any asset directories; then we are non-interactive
    if args.asset_directory:
        print("non interactive")
        directories = [os.path.abspath(x) for x in args.asset_directory]
        _init(conf, directories, data_url_default, 'sha512')
        exit(0)

    # **
    # ** run the install interactive script
    # **

    prompt("Initalize a new checker server at {} [Yes/no]?".format(conf),
           confirm_or_die)

    directories = multi_prompt(
        "Enter directories(s) or file(s) to watch, one per line",
        valid_path,
    )
    print(directories)

    data_url = default(
        "Enter data_url for persisted fixity data",
        data_url_default,
        # check that it is a valid URL
    )
    print(data_url)

    print(hashlib.algorithms)

    hash = default(
        'Pick a hashlib',
        'sha512',
        lambda x : x in hashlib.algorithms + ('',),
        ' '.join(hashlib.algorithms)
    )
    print(hash)

    _init(conf, directories, data_url, hash)


def _init(conf, directories, data_url, hash):
    """ set up the application directory """
    data = {
        '__name__': "{0}_{1}_conf".format(APP_NAME, __version__),
        'archive_directories': directories,
        'data_url': data_url,
        'hashlib': [ hash ],
        'loglevel': 'INFO',
        'sleepiness': 1
    }
    os.mkdir(conf)
    os.mkdir(os.path.join(conf, 'logs'))
    with open(
        os.path.join(conf, 'conf_{0}.json'.format(APP_NAME)),
        'w',
    ) as outfile:
        json.dump(data, outfile, sort_keys=True,
                  indent=4, separators=(',', ': '))
    ## create .gitignore and activate(setting CHECKER_DIR)


def _parse_conf(args):
    conf = args.config_dir
    assert os.path.isdir(conf), \
        "configuration directory {0} does not exist, run init".format(conf)
    conf_file = os.path.join(conf, 'conf_{0}.json'.format(APP_NAME))
    assert os.path.isfile(conf_file), \
        "configuration file does not exist {0}, \
        not properly initialized".format(conf_file)
    with open(conf_file) as f:
        data = json.load(f)
    # validate data
    assert 'data_url' in data, \
        "data_url': '' not found in {0}".format(conf_file)
    assert 'archive_directories' in data, \
        "'archive_directories': [] not found in {0}".format(conf_file)

    # build up nested named tuple to hold parsed config 
    app_config = namedtuple('fixity',
        'data_url, archive_directories, json_dir, conf_file'
    )
    daemon_config = namedtuple('FixityDaemon', 'pid, log', )
    daemon_config.pid = os.path.abspath(os.path.join(conf, 'logs', '{0}.pid'.format(APP_NAME)))
    daemon_config.log = os.path.abspath(os.path.join(conf, 'logs', '{0}.log'.format(APP_NAME)))
    c = namedtuple('FixityConfig','app, daemon, args, data, conf_file')
    c.daemon = daemon_config
    c.args = args
    c.data = data
    c.conf_file = os.path.abspath(conf_file)
    return c


def show_conf(conf, ____):
    print()
    print('cursory check of {0} {1} config in "{2}" looks OK'.format(
        APP_NAME, __version__, conf.args.config_dir)
    )
    print("conf file")
    print('\t{0}'.format(conf.conf_file))
    print("pid file")
    print('\t{0}'.format(conf.daemon.pid))
    print("pid log")
    print('\t{0}'.format(conf.daemon.log))
    print("archive directories")
    for d in conf.data['archive_directories']:
        missing = ''
        if not(os.path.isdir(d) or os.path.isfile(d)):
            missing = '!! MISSING !!\a'
        print('\t{0} {1}'.format(d, missing))
    print()


def status(conf, daemon):
    daemon.do_action('status')
    # check for un-cleared errors

def update(conf, daemon):
    """ alter the truth to clear an error """
    # check if the server is running; if so, bail
    pp(args)


def json_report(conf, daemon):
    pp(args)


def json_load(conf, daemon):
    pp(args)


def start():
    pass


def stop():
    pass


def restart():
    pass


# ⌦
# ⌦   Functions for talking to the user during the init process
# ⌦


def prompt(prompt, validator=(lambda x: True), hint=None):
    """prompt the user for input
       :prompt: prompt text
       :validator: optional validation function
       :hint: optional hint for invalid answer
    """
    user_input = raw_input(prompt)
    while not validator(user_input):
        user_input = raw_input(prompt)
    return user_input


def default(prompt, default, validator=(lambda x: True), hint=None):
    """prompt the user for input, with default
       :prompt: prompt text
       :default: default to use if the user hits [enter]
       :validator: optional validation function
       :hint: optional hint for invalid answer
    """
    user_input = raw_input("{0} [{1}]".format(prompt, default))
    while not validator(user_input):
        user_input = raw_input("{0} [{1}]".format(prompt, default))
    return user_input or default


def multi_prompt(prompt, validator=(lambda x: x), hint=None):
    inputs = []
    print(prompt)
    user_input = raw_input('1 > ')
    while not validator(user_input):
        user_input = os.path.expanduser(raw_input('1 > '))
    inputs.append(os.path.abspath(user_input))

    for i in range(2, 10):
        sub_prompt = '{0} > '.format(i)
        user_input = os.path.expanduser(raw_input(sub_prompt))
        # the user might not have anything more to say
        if not user_input:
            break
        while not validator(user_input):
            user_input = os.path.expanduser(raw_input(sub_prompt))
        inputs.append(os.path.abspath(user_input))

    return inputs


# ⌦
# ⌦   Functions for validating user input
# ⌦


def confirm_or_die(string):
    valid = string.lower() in ['', 'y', 'ye', 'yes']
    decline = string.lower() in ['n', 'no']
    if valid:
        return True
    elif decline:
        sys.exit(1)
    else:
        print('please answer yes or no, [ENTER] for yes')


def valid_path(string):
    path = os.path.expanduser(string)
    valid = os.path.isfile(path) or os.path.isdir(path)
    if valid:
        return valid
    else:
        print('directory of file must exist')


# ⌦
# ⌦  file checking functions
# ⌦


def check_one_arg(filein, observations, hash, update, conf):
    """check if the arg is a file or directory, walk directory for files"""
    if os.path.isdir(filein):
        for root, ____, files in os.walk(filein):
            for f in files:
                fullpath = os.path.join(root, f)
                check_one_file(fullpath, observations, hash, update, conf)
    else:
        check_one_file(filein, observations, hash, update, conf)


def check_one_file(filein, observations, hash, update, conf):
    """check file one file against our memories"""
    startTime = time.time()
    filename = os.path.abspath(filein)
    logging.info('{0}'.format(filename))
    # normalize filename, take hash for key
    filename_key = hashlib.sha224(filename.encode('utf-8')).hexdigest()
    logging.debug('sha224 of path {0}'.format(filename_key))

    seen_now = analyze_file(filename, hash)
    logging.debug('seen_now {0}'.format(seen_now))

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
            logging.debug('new memory {0}'.format(memory))
    else:
        # update observations
        observations[filename_key] = seen_now
        observations.sync()
        logging.info('update observations')

    elapsedTime = time.time() - startTime
    time.sleep(os.getloadavg()[0] * elapsedTime * conf.data['sleepiness'])


def compare_sightings(now, before, news={}):
    """ return False if sightings differ, otherwise True """
    logging.debug('now {0} before {1}'.format(now, before))
    if not now['size'] == before['size']:
        logging.error('sizes do not match')
        return False
    for check in list(now.keys()):
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


def log_nice(conf):
    """ some ugly incantations to run nice and set up logging"""
    # set debugging level
    numeric_level = getattr(logging, conf.data['loglevel'], None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(
        filename=conf.daemon.log,
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    # ionice... http://stackoverflow.com/a/6245160/1763984
    p = psutil.Process(os.getpid())
    # ... if we can http://stackoverflow.com/a/34472/1763984
    if hasattr(p, 'set_ionice'):
        p.set_ionice(psutil.IOPRIO_CLASS_IDLE)

    os.nice(10)


def fixity_checker_report_command(argv=None):
    """ main for report generator """
    parser = argparse.ArgumentParser(description=''.join(['Yet another fixity checker ', __version__]))
    parser.add_argument('outputdir', nargs=1, help='file or directory',)
    parser.add_argument('--data_url',
                        help='database URL to shove to (file://... for files)',
                        default=DATA)
    parser.add_argument('--loglevel', default='ERROR')

    if argv is None:
        argv = parser.parse_args()

    nice_log(argv.loglevel.upper())
    # persisted dict interface for long term memory
    observations = Shove(argv.data_url, protocol=PICKLE_PROTOCOL, flag='r')

    fixity_checker_report(observations, argv.outputdir[0])

    observations.close()


def fixity_checker_report(observations, outputdir):
    """ output a listing of our memories """
    logging.debug("{0}, {1}".format(observations, outputdir))
    shards = defaultdict(dict)
    _mkdir(outputdir)
    # sort into bins for transport
    for key, value in list(observations.items()):
        shard_key = key[:2]
        shards[shard_key].update({key: value})
    # write out json for each bin
    for key, value in list(shards.items()):
        out = os.path.join(outputdir, ''.join([key, '.json']))
        with open(out, 'w') as outfile:
            json.dump(shards[key], outfile, sort_keys=True,
                      indent=4, separators=(',', ': '))


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """  # http://code.activestate.com/recipes/82465-a-friendly-mkdir/
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired "
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        # print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)


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

