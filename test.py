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
        # run the checker
        argv = argparse.Namespace()
        argv.filepath = ['test-data',]
        argv.loglevel = 'ERROR'
        argv.data_url = ''.join(['file://', os.path.join(self.workspace,'shove')])
        argv.hashlib = 'md5'
        argv.update = None
        self.assertTrue(fixity_checker.main(argv) == None)
        self.assertTrue(fixity_checker.main(argv) == None)

        # run the reporter
        argv2 = argparse.Namespace()
        argv2.loglevel = 'ERROR'
        argv2.data_url = ''.join(['file://', os.path.join(self.workspace,'shove')])
        od = os.path.join(self.workspace,'test-report')
        argv2.outputdir = [od,]
        self.assertTrue(fixity_checker.fixity_checker_report_command(argv2) == None)
        f = [files for ____, ____, files in os.walk(od)][0][0]
        self.assertTrue(f.endswith('.json'))
        self.assertTrue(os.path.isfile(os.path.join(od,f)))


class TestCompare(unittest.TestCase):
    def test_compare(self):
        sight = fixity_checker.compare_sightings
        a1 = { 'size': 1 }
        a2 = { 'size': 2 }
        b = { 'size': 1, 'md5': 'xyz' } # pretend we just saw this <--
        bb = { 'size': 1, 'md5': 'xyz', 'path': '/path/' }
        bc = { 'size': 1, 'md5': 'xyz', 'path': '/path2/' }
        c = { 'size': 1, 'md5': 'abc' }      
        #                     | <- this time I see
        #                     | | <- what I remember from last time
        self.assertTrue(sight(b,b))          # no change since last time
        self.assertTrue(sight(b,bb))         # no change since last time (with path in the database)
        news = {}                            # got some news?
        self.assertTrue(sight(bb,b,news))    # 
        self.assertTrue(any(news))
        self.assertFalse(sight(bc,bb))       # path is not the same
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
