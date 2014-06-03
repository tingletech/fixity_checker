import fixity_checker
import unittest
from pprint import pprint as pp
import argparse
import tempfile
import shutil
import os

# 
class TestCommand(unittest.TestCase):

    def setUp(self):
        self.workspace = tempfile.mkdtemp(prefix='yafixity-test-')

    def tearDown(self):
        shutil.rmtree(self.workspace)

    def test_integration(self):
        argv = argparse.Namespace()
        argv.filepath = ['.',]
        argv.loglevel = 'ERROR'
        argv.cache_url = ''.join(['file://', os.path.join(self.workspace,'shove')])
        argv.hashlib = 'md5'
        argv.update = None
        pp(argv)
        fixity_checker.main(argv)

class TestCompare(unittest.TestCase):
    def test_compare(self):
        sight = fixity_checker.compare_sightings
        a1 = { 'size': 1 }
        a2 = { 'size': 2 }
        b = { 'size': 1, 'md5': 'xyz' } # pretend we just saw this <--
        bb = { 'size': 1, 'md5': 'xyz', 'path': '/path/' }
        c = { 'size': 1, 'md5': 'abc' }
        assert(sight(b,b))          # no change since last time
        assert(sight(b,bb))         # no change since last time (with path in the database)
        assert(sight(b,a1))         # have seen this file, but not this checksum type
        assert(not(sight(b,a2)))    # new sighting with changed size
        assert(not(sight(b,c)))     # new sighting with changed checksum

class TestObserve(unittest.TestCase):
    pass
