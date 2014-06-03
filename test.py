import fixity_checker
import unittest
from pprint import pprint as pp
import argparse
import tempfile
import shutil
import os
# from shove import Shove

# 
class TestCommand(unittest.TestCase):

    def setUp(self):
        self.workspace = tempfile.mkdtemp(prefix='yafixity-test-')

    def tearDown(self):
        shutil.rmtree(self.workspace)

    def test_integration(self):
        argv = argparse.Namespace()
        argv.filepath = ['test-data',]
        argv.loglevel = 'ERROR'
        argv.cache_url = ''.join(['file://', os.path.join(self.workspace,'shove')])
        argv.hashlib = 'md5'
        argv.update = None
        self.assertTrue(fixity_checker.main(argv))
        self.assertTrue(fixity_checker.main(argv))

        # alter our memories, retry should fail
        # observations = Shove(argv.cache_url)
        # key, value = [value for value in observations.iteritems()][0]
        # value['md5'] = 'xyz'
        # observations[key] = value
        # observations.sync()
        # fixity_checker.main(argv)
        # self.assertRaises(AssertionError, fixity_checker.main(argv))

class TestCompare(unittest.TestCase):
    def test_compare(self):
        sight = fixity_checker.compare_sightings
        a1 = { 'size': 1 }
        a2 = { 'size': 2 }
        b = { 'size': 1, 'md5': 'xyz' } # pretend we just saw this <--
        bb = { 'size': 1, 'md5': 'xyz', 'path': '/path/' }
        c = { 'size': 1, 'md5': 'abc' }
        self.assertTrue(sight(b,b))          # no change since last time
        self.assertTrue(sight(b,bb))         # no change since last time (with path in the database)
        self.assertTrue(sight(b,a1))         # have seen this file, but not this checksum type
        self.assertFalse(sight(b,a2))        # new sighting with changed size
        self.assertFalse(sight(b,c))         # new sighting with changed checksum

class TestObserve(unittest.TestCase):
    def test_observe(self):
        sight = fixity_checker.compare_sightings
        analyze_file = fixity_checker.analyze_file
        # 139367 test-data/loc/2478433644_2839c5e8b8_o_d.jpg
        # MD5 (test-data//loc/2478433644_2839c5e8b8_o_d.jpg) = 9a2b89e9940fea6ac3a0cc71b0a933a0
        self.assertTrue(sight(analyze_file('test-data/loc/2478433644_2839c5e8b8_o_d.jpg', 'md5'),{
            'size': 139367,
            'md5': '9a2b89e9940fea6ac3a0cc71b0a933a0'
        }))
        # 326929 test-data/si/4011399822_65987a4806_b_d.jpg
        # MD5 (test-data//si/4011399822_65987a4806_b_d.jpg) = 5580eaa31ad1549739de12df819e9af8
        self.assertTrue(sight(analyze_file('test-data/loc/3314493806_6f1db86d66_o_d.jpg', 'md5'),{
            'size': 143435,
            'md5': '6172e980c2767c12135e3b9d246af5a3'
        }))
        # 143435 test-data/loc/3314493806_6f1db86d66_o_d.jpg
        # MD5 (test-data//loc/3314493806_6f1db86d66_o_d.jpg) = 6172e980c2767c12135e3b9d246af5a3
        self.assertTrue(sight(analyze_file('test-data/si/2584174182_ffd5c24905_b_d.jpg', 'md5'),{
            'size': 381813,
            'md5': '38a84cd1c41de793a0bccff6f3ec8ad0'
        }))
        # 381813 test-data/si/2584174182_ffd5c24905_b_d.jpg
        # MD5 (test-data//si/2584174182_ffd5c24905_b_d.jpg) = 38a84cd1c41de793a0bccff6f3ec8ad0
        self.assertTrue(sight(analyze_file('test-data/si/4011399822_65987a4806_b_d.jpg', 'md5'),{
            'size': 326929,
            'md5': '5580eaa31ad1549739de12df819e9af8'
        }))
