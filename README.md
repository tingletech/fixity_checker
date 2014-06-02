
```
(ve)$ ./checkfile.py checkfile.py 
(ve)$ ./checkfile.py checkfile.py --cache_url sqlite:///fixity.db --loglevel info
INFO:root:/Users/tingle/code/fixity/checkfile.py
INFO:root:update observations
(ve)$ ./checkfile.py checkfile.py --cache_url sqlite:///fixity.db --loglevel info
INFO:root:/Users/tingle/code/fixity/checkfile.py
(ve)$ echo "" >> checkfile.py 
(ve)$ ./checkfile.py checkfile.py --cache_url sqlite:///fixity.db --loglevel info
INFO:root:/Users/tingle/code/fixity/checkfile.py
ERROR:root:sizes do not match
Traceback (most recent call last):
  File "./checkfile.py", line 99, in <module>
    sys.exit(main())
  File "./checkfile.py", line 57, in main
    assert bool(looks_the_same), "%r has changed" % filename
AssertionError: '/Users/tingle/code/fixity/checkfile.py' has changed
```
