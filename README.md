# Yet another fixity checker

Designed to be run from `cron` on unix.  Will exit non-zero if anything
looks wrong (unless `--update` option is given).

## install
```
pip install https://github.com/tingletech/fixity/archive/master.tar.gz
```

[![Build Status](https://travis-ci.org/tingletech/fixity.svg)](https://travis-ci.org/tingletech/fixity)

## use

Supply the name(s) of files or directories to check.
```
usage: checker [-h] [--update] [--data_url DATA_URL] [--hashlib HASHLIB]
               [--loglevel LOGLEVEL]
               filepath [filepath ...]
```

### --hashlib
 * at least `md5`, `sha1`, `sha224`, `sha256`, `sha384`, and `sha512` will always be present
 * supports any hash available to [`hashlib`](https://docs.python.org/2/library/hashlib.html#module-hashlib)

### --data_url

How should we record our observations? 

 * <b>supported backends</b> via [shove](https://pypi.python.org/pypi/shove)
 Amazon S3 Web Service, Apache Cassandra, Berkeley Source Database,
 DBM, Durus, FTP, Filesystem, Firebird, git, HDF5, LevelDB, Memory,
 Mercurial, Microsoft SQL Server, MongoDB, MySQL, Oracle, PostgreSQL,
 Redis, SQLite, Subversion, Zope Object Database (ZODB)
 * use [SQLAlchemy syntax for database URLs](http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html)

for example `file://rel` `file:////full/path` `git://rel` <-- like file, but keeps it in revision control

## Report

To output a report in JSON, specify a directory

```
usage: fixity_checker_report [-h] [--data_url DATA_URL] [--loglevel LOGLEVEL]
                             outputdir
```
