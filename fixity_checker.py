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
from collections import namedtuple, defaultdict
import logging
import logging.handlers
from shove import Shove
import hashlib
import psutil
import cStringIO
import urlparse

# raw_import() in 2 -> import() in 3
try:
    input = raw_input
except NameError:
    pass

# use readline if it is available for interactive input in init
try:
    import readline   # noqa
except ImportError:
    pass

try:
    import boto
    import boto.s3.key
except ImportError:
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
    parser = argparse.ArgumentParser(
        epilog='using CHECKER_DIR="{0}"; use -d dir after \
        subcommand or change env to use different config \
        dir\n\t{1} {2}'.format(CHECKER_DIR, APP_NAME, __version__)
    )

    subparsers = parser.add_subparsers(dest='subparser_name')

    # **
    # ** list all subcommands and what they do
    # **

    commands = [
        ('init', 'runs and interactive script to configure a checker server'),
        ('show_conf', 'validate and show configuration options'),
        ('start', 'starts the checker server'),
        ('stop', 'stops the checker server'),
        ('status', 'produces a report of the server status'),
        ('errors', 'reports on any fixity errors that have been found'),
        ('extent', 'files / bytes under observation'),
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
        if command not in ['start', 'stop', 'restart', 'update']:
            # map sub command to the function named _command_ in this file
            parsers[command].set_defaults(func=getattr(thismodule, command))

    # some subcommands need custom arguments
    parsers['start'].add_argument('--no-detach', dest='detach', action='store_false')
    parsers['update'].add_argument('file', nargs='+', help='file(s) to update')
    parsers['json_report'].add_argument('report_directory', nargs=1)
    parsers['json_load'].add_argument('report_directory', nargs=1)
    parsers['init'].add_argument('--archive_paths', nargs='+',
                                 dest='archive_paths',
                                 help='directories to check')
    group = parsers['show_conf'].add_mutually_exclusive_group()
    group.add_argument('--log_file', action='store_true')
    group.add_argument('--pid_file', action='store_true')
    group.add_argument('--dir', action='store_true')

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

    # will fail if the conf does not parse
    conf = _parse_conf(argv)

    # start to set up daemon
    detach = True
    if 'detach' in argv:
        detach = argv.detach
    if sys.argv[1] == 'update':
        detach = False

    # callbacks for daemon
    def main_loop_wrapper():
        # nested here to gain access to `conf`
        log_nice(conf)
        logging.info('Daemon is starting')
        while True:
            checker(conf)

    def cb_shutdown(message, code):
        # don't have access to observations or errror here; pull these out 
        # a level so we can close them?
        if conf.args.subparser_name != 'update':
            logging.info('Daemon is stopping')
            logging.debug(message)

    daemon = daemonocle.Daemon(
        worker=main_loop_wrapper,
        workdir=os.getcwd(),
        shutdown_callback=cb_shutdown,
        pidfile=conf.daemon.pid,
        detach=detach
    )

    if sys.argv[1] in ['start', 'stop', 'restart']:
        daemon.do_action(sys.argv[1])
    elif sys.argv[1] == 'update':
        daemon.do_action('start')
    else:
        return argv.func(conf, daemon)


def checker(conf):
    """ the main loop """
    startLoopTime = time.time()
    # persisted dict interface for long term memory
    observations = Shove(conf.data['data_url'], protocol=2)
    errors = Shove('file://{0}'.format(conf.app.errors), protocol=2,)


    # %%
    # %% update the database and quit
    # %% 
    if conf.args.subparser_name == 'update':
        logging.warning('altering memories')
        for f in conf.args.file:
            path = os.path.abspath(f)
            print(path)
            for hashtype in conf.data['hashlib']:
                check_one_file(path, observations, hashtype, True, conf, errors)
                observations.sync()
            filename_key = hashlib.sha224(path.encode('utf-8')).hexdigest()
            errors.pop(filename_key, None)
            errors.sync()
        observations.close()
        errors.close()
        exit(0)

    # counts

    # for each hash type
    for hashtype in conf.data['hashlib']:
        logging.info('starting {0} checks'.format(hashtype))
        # for each command line argument
        for filepath in conf.data['archive_paths']:
            assert filepath, "arguments can't be empty"
            filepath = filepath+''  # http://fomori.org/blog/?p=486

            check_one_arg(filepath, observations, hashtype, False, conf, errors)

    # check for missing files
    logging.info('looking for missing files')
    for ____, value in list(observations.items()):
        if value['path'].startswith('s3://'):
            # TODO: check to make sure this file is still on s3
            pass
            # TODO: check to make sure this file is still on s3
        elif not os.path.isfile(value['path']):
            track_error(value['path'],
                        "{0} no longer exists or is not a file".format(value['path']),
                        errors)

    # output json reports
    fixity_checker_report(observations, conf.app.json_dir)
    observations.close()
    logging.info('writting reports at {0}'.format(conf.app.json_dir))

    elapsedLoopTime = time.time() - startLoopTime
    # logging.info("elapsedLoopTime {0} {1} files {2} bytes".format(elapsedLoopTime))
    logging.info("elapsedLoopTime {0}".format(elapsedLoopTime))

    if elapsedLoopTime < conf.data['min_loop']:
        nap = conf.data['min_loop'] - elapsedLoopTime
        logging.info('sleeping for {0}'.format(nap))
        time.sleep(nap)


def track_error(path, message, errors):
    logging.warning(message)
    filename_key = hashlib.sha224(path.encode('utf-8')).hexdigest()
    note = { message: True }
    if filename_key in errors:
        errors[filename_key].update(note)
    else:
        errors[filename_key] = note
    errors.sync()

# ⌦
# ⌦  following functions impliment subcommands
# ⌦


def init(args):
    """ setup wizard """
    conf = args.config_dir

    # don't run more than once
    assert not(os.path.exists(conf)), \
        "{0} directory specified for init must not exist".format(conf)

    data_url_default = 'file://{0}/'.format(os.path.abspath(
                                           os.path.join(conf,
                                                        'fixity_data_raw')))

    if args.archive_paths:
        directories = [os.path.abspath(x) for x in args.archive_paths]
        _init(conf, directories, data_url_default, 'sha512')
        show_conf(_parse_conf(args), None)
        exit(0)

    # **
    # ** run the install interactive script
    # **

    prompt("Initalize a new checker server at {0} [Yes/no]?".format(conf),
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

    try:
        hashlib_algorithms = hashlib.algorithms
    except:
        hashlib_algorithms = tuple(hashlib.algorithms_available)

    pp(list(hashlib_algorithms))

    hash = default(
        'Pick a hashlib',
        'sha512',
        lambda x : x in hashlib_algorithms + ('',),
        ' '.join(hashlib_algorithms)
    )
    print(hash)

    _init(conf, directories, data_url, hash)
    show_conf(_parse_conf(args), None)


def _init(conf, directories, data_url, hash):
    """ set up the application directory """
    data = {
        '__name__': "{0}_{1}_conf".format(APP_NAME, __version__),
        'archive_paths': directories,
        'data_url': data_url,
        'hashlib': [ hash ],
        'loglevel': 'INFO',
        'min_loop': 43200,          # twice a day
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
    with open(
        os.path.join(conf, 'activate'),
        'w',
    ) as outfile:
        outfile.write('export CHECKER_DIR={0}'.format(conf))


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
    assert 'archive_paths' in data, \
        "'archive_paths': [] not found in {0}".format(conf_file)

    # build up nested named tuple to hold parsed config 
    app_config = namedtuple('fixity',
        'json_dir, conf_file, errors',
    )
    daemon_config = namedtuple('FixityDaemon', 'pid, log', )
    daemon_config.pid = os.path.abspath(
        os.path.join(conf, 'logs', '{0}.pid'.format(APP_NAME)))
    daemon_config.log = os.path.abspath(
        os.path.join(conf, 'logs', '{0}.log'.format(APP_NAME)))
    app_config.json_dir = os.path.abspath(os.path.join(conf, 'json_dir'))
    app_config.errors = os.path.abspath(os.path.join(conf, 'errors'))
    c = namedtuple('FixityConfig','app, daemon, args, data, conf_file')
    c.app = app_config
    c.daemon = daemon_config
    c.args = args
    c.data = data
    c.conf_file = os.path.abspath(conf_file)
    return c


def show_conf(conf, ____):
    if 'log_file' in conf.args and conf.args.log_file:
        print(conf.daemon.log)
        exit(0)
    if 'pid_file' in conf.args and conf.args.pid_file:
        print(conf.daemon.pid)
        exit(0)
    if 'dir' in conf.args and conf.args.dir:
        print(os.path.abspath(conf.args.config_dir))
        exit(0)
    print()
    print('cursory check of {0} {1} config in "{2}" looks OK'.format(
        APP_NAME, __version__, conf.args.config_dir)
    )
    print("conf file")
    print('\t{0}'.format(conf.conf_file))
    print("pid file")
    print('\t{0}'.format(conf.daemon.pid))
    print("log file")
    print('\t{0}'.format(conf.daemon.log))
    print("archive paths")
    for d in conf.data['archive_paths']:
        missing = ''
        if not(os.path.isdir(d) or os.path.isfile(d)):
            missing = '!! MISSING !!\a'
        print('\t{0} {1}'.format(d, missing))
    print()


def status(conf, daemon):
    """daemon and fixity status report"""
    # daemonocle exit's 0 when 'not running', capture STDOUT
    # http://stackoverflow.com/a/1983450/1763984
    def captureSTDOUT(thefun, *a, **k):
        savstdout = sys.stdout
        sys.stdout = cStringIO.StringIO()
        try:
            thefun(*a, **k)
        finally:
            v = sys.stdout.getvalue()
            sys.stdout = savstdout
        return v

    output = captureSTDOUT(daemon.do_action, 'status')
    print(output)
    if 'not running' in output:
        exit(2)


def errors(conf, daemon):
    """ check for un-cleared errors with files"""
    # persisted dict interface for long term memory
    errors = Shove('file://{0}'.format(conf.app.errors), protocol=2, flag='r')
    if any(errors):
        print("errors found")
        for path, error in list(errors.items()):
            pp(error)
        errors.close()
        exit(1)
    else:
        print("no errors found - OK")
        print()
        errors.close()


def json_report(conf, daemon):
    # persisted dict interface for long term memory
    observations = Shove(conf.data['data_url'], protocol=2, flag='r')
    fixity_checker_report(observations, conf.args.report_directory[0])
    observations.close()


def extent(conf, daemon):
    observations = Shove(conf.data['data_url'], protocol=2, flag='r')
    count = namedtuple('Counts', 'files, bytes, uniqueFiles, uniqueBytes')
    count.bytes = count.files = count.uniqueFiles = count.uniqueBytes = 0
    dedup = {}
    for key, value in list(observations.items()):
        count.files = int(count.files) + 1
        count.bytes = count.bytes + value['size']
        hash_a = conf.data['hashlib'][0]
        hash_v = value[hash_a]
        if not(hash_v in dedup):
            count.uniqueFiles = count.uniqueFiles + 1
            count.uniqueBytes = count.uniqueBytes + value['size']
        dedup[hash_v] = value['size']
    observations.close()
    def sizeof_fmt(num):
        # http://stackoverflow.com/a/1094933/1763984
        for x in ['bytes','KiB','MiB','GiB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TiB')
    print('observing {0} files {1} bytes ({2}) | unique {3} files {4} bytes ({5})'.format(
        count.files, count.bytes, sizeof_fmt(count.bytes),
        count.uniqueFiles, count.uniqueBytes, sizeof_fmt(count.uniqueBytes)))
    print()


def json_load(conf, daemon):
    pp(conf.args)
    print("not implimented")


# ⌦
# ⌦   Functions for talking to the user during the init process
# ⌦


def prompt(prompt, validator=(lambda x: True), hint=None):
    """prompt the user for input
       :prompt: prompt text
       :validator: optional validation function
       :hint: optional hint for invalid answer
    """
    user_input = input(prompt)
    while not validator(user_input):
        user_input = input(prompt)
    return user_input


def default(prompt, default, validator=(lambda x: True), hint=None):
    """prompt the user for input, with default
       :prompt: prompt text
       :default: default to use if the user hits [enter]
       :validator: optional validation function
       :hint: optional hint for invalid answer
    """
    user_input = input("{0} [{1}]".format(prompt, default))
    while not validator(user_input):
        user_input = input("{0} [{1}]".format(prompt, default))
    return user_input or default


def multi_prompt(prompt, validator=(lambda x: x), hint=None):
    inputs = []
    print(prompt)
    user_input = input('1 > ')
    while not validator(user_input):
        user_input = os.path.expanduser(input('1 > '))
    inputs.append(os.path.abspath(user_input))

    for i in range(2, 10):
        sub_prompt = '{0} > '.format(i)
        user_input = os.path.expanduser(input(sub_prompt))
        # the user might not have anything more to say
        if not user_input:
            break
        while not validator(user_input):
            user_input = os.path.expanduser(input(sub_prompt))
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


def check_one_arg(filein, observations, hash, update, conf, errors):
    """check if the arg is a file or directory, walk directory for files"""
    if filein.startswith('s3://'):
        check_s3_url(filein, observations, hash, update, conf, errors)
    elif os.path.isdir(filein):
        for root, ____, files in os.walk(filein):
            for f in files:
                fullpath = os.path.join(root, f)
                check_one_file(fullpath, observations, hash, update, conf, errors)
    else:
        check_one_file(filein, observations, hash, update, conf, errors)


def check_s3_url(bucketurl, observations, hash, update, conf, errors):
    s3 = boto.connect_s3()
    # SplitResult(scheme='s3', netloc='test.pdf', path='/dkd', query='', fragment='')
    parts = urlparse.urlsplit(bucketurl)  
    bucket = s3.lookup(parts.netloc)
    #bucket = s3.get_bucket(parts.netloc)
    for key in bucket.list():
        # look for pdfs that match the user supplied path
        if not parts.path or key.name.startswith(parts.path[1:]):
            # The Key object in boto, which represents on object in S3,
            # can be used like an iterator http://stackoverflow.com/a/7625197/1763984
            check_one_file(key, observations, hash, update, conf, errors)


def check_one_file(filein, observations, hash, update, conf, errors):
    """check one file (or s3 key) against our memories"""
    startTime = time.time()

    filename = ""
    s3 = False
    # do I have a local filesystem path or s3 bucket key?
    if type(filein) is unicode:
        filename = os.path.abspath(filein)
    try:
        if type(filein) is boto.s3.key.Key:
            s3 = True
            filename = 's3://{0}/{1}'.format(filein.bucket.name,
                                            filein.name)
    except NameError:
        pass

    filename_key = hashlib.sha224(filename.encode('utf-8')).hexdigest()
    logging.info('{0}'.format(filename))

    # normalize filename, take hash for key
    logging.debug('sha224 of path {0}'.format(filename_key))

    if s3:
        seen_now = analyze_s3_key(filein, hash)
    else:
        seen_now = analyze_file(filename, hash)

    logging.debug('seen_now {0}'.format(seen_now))

    if filename_key in observations and not update:
        # make sure things match
        news = {}
        looks_the_same = compare_sightings(
            seen_now, observations[filename_key], news
        )
        if not looks_the_same:
            track_error(filename, "%r has changed" % filename, errors)
        if any(news):
            update = observations[filename_key]
            update.update(news)
            observations[filename_key] = update
            observations.sync()
            logging.debug('new memory {0}'.format(news))
    else:
        # update observations
        observations[filename_key] = seen_now
        observations.sync()
        logging.info('update observations')

    # take a nap, for longer if the system load is high
    elapsedTime = time.time() - startTime
    load = os.getloadavg()[0]
    nap = load * elapsedTime * conf.data['sleepiness']
    logging.debug('napping for {0}, load {1}'.format(nap, load))
    time.sleep(nap)


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


def analyze_s3_key(key, hashtype):
    """ returns a dict of hash and size in bytes """
    hasher = hashlib.new(hashtype)
    BLOCKSIZE = 1024 * hasher.block_size
    buf = key.read(BLOCKSIZE)
    while len(buf) > 0:
        hasher.update(buf)
        buf = key.read(BLOCKSIZE)
    # in the future, add os.POSIX_FADV_DONTNEED support
    # needs python 3 and newer linux kernel
    # http://www.gossamer-threads.com/lists/python/python/1063241
    return {
        'size': key.size,
        hasher.name: hasher.hexdigest(),
        'path': 's3://{0}/{1}'.format(key.bucket.name, key.name),
    }


def log_nice(conf):
    """ some ugly incantations to run nice and set up logging"""
    # set debugging level
    numeric_level = getattr(logging, conf.data['loglevel'], None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % conf.data['loglevel'])

    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    rh = logging.handlers.TimedRotatingFileHandler(conf.daemon.log, when='midnight',)
    rh.setLevel(numeric_level)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    rh.setFormatter(formatter)
    logger.addHandler(rh)

    # ionice... http://stackoverflow.com/a/6245160/1763984
    p = psutil.Process(os.getpid())
    # ... if we can http://stackoverflow.com/a/34472/1763984
    if hasattr(p, 'set_ionice'):
        p.set_ionice(psutil.IOPRIO_CLASS_IDLE)

    os.nice(10)


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
