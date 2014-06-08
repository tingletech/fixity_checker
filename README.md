# Yet another fixity checker

fixity checking daemon


_for Python versions 2.6, 2.7, 3.3, 3.4_

## install
```
pip install https://github.com/tingletech/fixity/archive/master.tar.gz
```

[![Build Status](https://travis-ci.org/tingletech/fixity.svg)](https://travis-ci.org/tingletech/fixity)

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
    status              produces a report of the server status and any errors
    restart             stop follow by a start
    update              updates fixity info (server must be stopped)
    json_report         json serialization of application data
    json_load           load json serialization into application data

optional arguments:
  -h, --help            show this help message and exit
```


# Related work

see https://github.com/tingletech/fixity/wiki
