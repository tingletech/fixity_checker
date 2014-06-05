# Yet another fixity checker

Designed to be run from `cron` on unix.  Will exit non-zero if anything
looks wrong (unless `--update` option is given).

_for Python versions 2.6, 2.7, 3.3, 3.4_

## install
```
pip install https://github.com/tingletech/fixity/archive/master.tar.gz
```

[![Build Status](https://travis-ci.org/tingletech/fixity.svg)](https://travis-ci.org/tingletech/fixity)

## use

Supply the name(s) of files or directories to check.  Directories
are recursively searched for files to check.  Files that have not been seen
before are noted, files that have been seen before are checked.

After checking all files and directories supplied on the command
line, the existance of all files ever noted is verified.

The command exits with a non-zero exit code (unsuccessful) if any
file has changed or is missing.  No STDOUT/STDERR is produced and
an exit code of 0 is issued upon successful execution.  Running
this from the crontab will cause an email to be sent if files change
or go missing.

TODO: better alerts (email, Amazon SNS, growl)

```
usage: checker [-h] [--update] [--data_url DATA_URL] [--hashlib HASHLIB]
               [--loglevel LOGLEVEL]
               filepath [filepath ...]
```

### --hashlib
 * `sha512` by default
 * at least `md5`, `sha1`, `sha224`, `sha256`, `sha384`, and `sha512` will always be present
 * supports any hash available to [`hashlib`](https://docs.python.org/2/library/hashlib.html#module-hashlib)

### --data_url

By default application data will be stored in a platform-specific
"user data dir" as specified by
[`appdirs`](https://pypi.python.org/pypi/appdirs/).  You may specify
an alternative location or backend with this parameter.

 * <b>supported backends</b> via [shove](https://pypi.python.org/pypi/shove)
 Amazon S3 Web Service, Apache Cassandra, Berkeley Source Database,
 DBM, Durus, FTP, Filesystem, Firebird, git, HDF5, LevelDB, Memory,
 Mercurial, Microsoft SQL Server, MongoDB, MySQL, Oracle, PostgreSQL,
 Redis, SQLite, Subversion, Zope Object Database (ZODB)
 * use [SQLAlchemy syntax for database URLs](http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html)

for example `file://relative/path` `file:///full/path` `git://rel` <-- like file, but keeps it in revision control


## Report

To output a report in JSON, specify a directory

```
usage: fixity_checker_report [-h] [--data_url DATA_URL] [--loglevel LOGLEVEL]
                             outputdir
```

A series of `.json` files serializing the contents of the application's
persistent data will be created in the output directory.

The `.json` is sorted and spaced in a way that is hoped to make it work will
with revision control system such as `git`.  `git`'s support of digital 
signatures and revision history could be used to support audit requirements.

TODO: write a loader to read the output `.json` files back in.

# Related work

see https://github.com/tingletech/fixity/wiki
