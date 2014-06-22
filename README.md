# Yet another fixity checker

fixity checking daemon


_for Python versions 2.6, 2.7, 3.3, 3.4_

 * `checker start | stop | restart | status` runs as a daemon, no worries about cron jobs running over each other, just let this run all the time.
   * slow and steady wins the race: `checker` is designed to be super nice so it can run 24/7 with minimal impact (runs `nice`, `ionice` Idle scheduler, and a special "sleepiness" factor that is used along with cpu wait to determine `sleep` naps between work.)
 * `checker errors` fixity monitor; alerts if any anomalies are detected
 * `checker extent` file and byte counts, total and unique
 * `checker init` setup wizard and `checker show_conf` validator
 * can monitor local files and directories or AWS S3 `s3://bucket/[path]`


## install
```
pip install https://github.com/tingletech/fixity_checker/archive/master.tar.gz
```

[![Build Status](https://travis-ci.org/tingletech/fixity_checker.svg)](https://travis-ci.org/tingletech/fixity_checker)

## use

```
usage: fixity_checker.py [-h]
   
                         {init,show_conf,start,stop,status,restart,update,json_report,json_load}
                         ...

positional arguments:
  {init,show_conf,start,stop,status,restart,update,json_report,json_load}
    init                runs and interactive script to configure a checker
                        server
    show_conf           validate and show configuration options
    start               starts the checker server
    stop                stops the checker server
    status              produces a report of the server status
    errors              reports on any fixity errors that have been found
    extent              files / bytes under observation
    restart             stop follow by a start
    update              updates fixity info (server must be stopped)
    json_report         json serialization of application data
    json_load           load json serialization into application data

optional arguments:
  -h, --help            show this help message and exit
```

### Configuration

set <code>CHECKER_DIR</code> environmental variable or use <code>-d CONFIG_DIR</code> option after subcommand 
to specify application and server configuration.

# Related work

see https://github.com/tingletech/fixity_checker/wiki/Related
