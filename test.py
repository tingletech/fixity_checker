import fixity_checker
import unittest
from pprint import pprint as pp
import argparse

# 
class TestCheck(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_integration(self):
        argv = argparse.Namespace()
        argv.filepath = ['.',]
        argv.loglevel = 'ERROR'
        argv.cache_url = 'file://test'
        argv.hashlib = 'md5'
        argv.update = None
        pp(argv)
        fixity_checker.main(argv)
