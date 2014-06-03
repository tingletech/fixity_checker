import fixity_checker
import unittest
from pprint import pprint as pp
import argparse
import tempfile
import shutil
import os

# 
class TestCheck(unittest.TestCase):

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
