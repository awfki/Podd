from datetime import datetime
from os import listdir, path, remove
import unittest
from unittest.mock import patch

from database import Database, Feed
from podcast import Podcast, Episode
import utilities as test_util

DATE = datetime(2017, 2, 8, 17, 0)
FUTURE_DATE = datetime(2018, 5, 1, 1, 1)
DIR_PATH = path.dirname(__file__)
DATABASE = path.join(path.dirname(path.abspath(__file__)), 'tests.db')
PODCAST = ['test podcast',
           'google.com',
           '/Users/Xander/Home/',
           '1969-12-31 17:00:00']
RYAN_URL = 'http://tangent.libsyn.com/rss'
GOLD_URL = 'http://www.goldmansachs.com/exchanges-podcast/feed.rss'
DIR = '/Users/Xander/Desktop'
RYAN, GOLD, PETERSON = test_util.load_test_objects()


class TestDatabase(unittest.TestCase):

    def setUp(self):
        Database.create(DATABASE)

    def tearDown(self):
        remove(DATABASE)

    def test_database_creation(self):
        self.assertIn('tests.db', listdir(path.dirname(__file__)))

    def test_options_retrieval(self):
        with Database(DATABASE) as db:
            options = db.options()
            self.assertEqual((True, '/Users/Xander/Podcasts'), options)

    def test_subscriptions_retrieval(self):
        with Database(DATABASE) as db:
            subs = db.subscriptions()
        self.assertEqual([], subs)

    def test_change_download_date(self):
        with Database(DATABASE) as db:
            db.add_podcast(*PODCAST)
        with Database(DATABASE) as db:
            db.change_download_date('12-12-12', 'test podcast')
        with Database(DATABASE) as db:
            column = db.fetch_single_column('date')
        self.assertIn('12-12-12', column)

    def test_change_option(self):
            with Database(DATABASE) as db:
                db.change_option('new_only', '0')
                db.change_option('base_directory', '/Users/Home/Xander')
            with Database(DATABASE) as db:
                new_only, base_directory = db.options()
            self.assertEqual(0, new_only)
            self.assertEqual('/Users/Home/Xander', base_directory)

    def test_fetch_single_column(self):
        with Database(DATABASE) as db:
            db.add_podcast(*PODCAST)
        with Database(DATABASE) as db:
            column = db.fetch_single_column('name')
        self.assertIn('test podcast', column)

    def test_add_subscription(self):
        with Database(DATABASE) as db:
            db.add_podcast(*PODCAST)
        with Database(DATABASE) as db:
            url, dl_dir, date = db.subscriptions()[0]
        self.assertEqual(url, 'google.com')
        self.assertEqual(dl_dir, '/Users/Xander/Home/')
        self.assertEqual(date, '1969-12-31 17:00:00')

    def test_remove_podcast(self):
        with Database(DATABASE) as db:
            db.add_podcast(*PODCAST)
        with Database(DATABASE) as db:
            db.remove_podcast(PODCAST[0]) # Podcast name
        with Database(DATABASE) as db:
            subs = db.subscriptions()
        self.assertEqual([], subs)


class TestFeed(unittest.TestCase):

    def setUp(self):
        test_util.create_test_objects()
        Database.create(DATABASE)

    def tearDown(self):
        remove(DATABASE)

    def test_add_bad_podcast(self):
            with Feed(DATABASE) as feed:
                feed.add('google.com')
                feed.add(['google.com', 'yahoo.com'])
            with Database(DATABASE) as db:
                subs = db.subscriptions()
            self.assertEqual(subs, [])

    @patch('feedparser.parse')
    def test_add_podcast(self, mock_method):
        with Feed(DATABASE) as podcast:
            mock_method.return_value = RYAN
            podcast.add(RYAN_URL)
            mock_method.return_value = GOLD
            podcast.add(GOLD_URL)
        with Database(DATABASE) as db:
            url, directory, date = db.subscriptions()[0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        self.assertGreater(date, DATE)
        self.assertEqual(RYAN_URL, url)

    @patch('feedparser.parse')
    def test_add_reversed_feed(self, mock_method):
        mock_method.return_value = GOLD
        with Feed(DATABASE) as podcast:
            podcast.add(GOLD_URL)
        with Database(DATABASE) as db:
            url, directory, date = db.subscriptions()[0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        self.assertGreater(date, DATE)
#
#     # TODO add method to test remove()
#     # TODO add method to test last_episode_only

    @patch('feedparser.parse')
    def test_print_subscriptions(self, mock_method):
        mock_method.return_value = RYAN
        no_podcasts = Feed(DATABASE).print_subscriptions()
        self.assertFalse(no_podcasts)
        with Feed(DATABASE) as feed:
            feed.add(RYAN_URL)
        podcasts = Feed(DATABASE).print_subscriptions()
        self.assertIsNotNone(podcasts)
        with Feed(DATABASE) as feed:
            podcasts_ = feed.print_subscriptions()
        self.assertIsNotNone(podcasts_)

    def test_print_options(self):
        with Feed(DATABASE) as feed:
            new_only, download_directory = feed.print_options()
        self.assertEqual(new_only, 1)
        self.assertEqual(download_directory, '/Users/Xander/Podcasts')

    def test_set_directory_options(self):
        with Feed(DATABASE) as feed:
            self.assertFalse(feed.set_directory_option('hello'))
            self.assertTrue(feed.set_directory_option(DIR_PATH))

    def test_set_catalog_option(self):
        with Feed(DATABASE) as feed:
            self.assertFalse(feed.set_catalog_option('hello'))
            self.assertTrue(feed.set_catalog_option('all'))


class TestPodcast(unittest.TestCase):

    @patch('feedparser.parse')
    def setUp(self, mock_method):
        mock_method.return_value = RYAN
        test_util.create_test_objects()
        Database.create(DATABASE)
        with Feed(DATABASE) as db:
            db.add(RYAN_URL)

    def tearDown(self):
        remove(DATABASE)

    # TODO figure out how to patch out the actual download functionality
    # @patch('urllib.request.urlretrieve')
    # @patch('feedparser.parse')
    # def test_downloader(self, fp_mock, urllib_mock):
    #     fp_mock.return_value = RYAN
    #     urllib_mock.return_value = 'filename'
    #
    #     with classes.Podcast(FUTURE_DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #         self.assertIsNone(pod.downloader())
    #     with classes.Podcast(DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #         self.assertIsInstance(pod.downloader(), tuple)

    # @patch('feedparser.parse')
    # def test_episode_image(self, fp_mock):
    #     fp_mock.return_value = RYAN
    #     entry1 = RYAN.entries[0]
    #     with Podcast(DATE, DIR_PATH, RYAN_URL) as pod:
    #         self.assertIsNotNone(pod._episode_image_link(entry1))
    #     fp_mock.return_value = PETERSON
    #     entry2 = PETERSON.entries[0]
    #     with Podcast(DATE, DIR_PATH, '') as pod:
    #         self.assertIsNone(pod._episode_image_link(entry2))
    #
    # @patch('feedparser.parse')
    # def test_episode_link(self, mock_obj):
    #     mock_obj.return_value = RYAN
    #     for entry in RYAN.entries:
    #         with miscfunctions.Podcast(DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #             self.assertIsNotNone(pod._audio_file_link(entry))
    #     for entry in GOLD.entries:
    #         with miscfunctions.Podcast(DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #             self.assertIsNotNone(pod._audio_file_link(entry))
    #     for entry in PETERSON.entries:
    #         with miscfunctions.Podcast(DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #             self.assertIsNotNone(pod._audio_file_link(entry))

    # @patch('feedparser.parse')
    # def test_mp3_tagger(self, mock_obj):
    #     class TestEpisode:
    #         filename = path.join(path.join(path.dirname(__file__), 'testfiles'), 'test.mp3')
    #         title = 'test title'
    #     mock_obj.return_value = RYAN
    #     with Podcast(DATE, DIR_PATH, RYAN_URL) as pod:
    #         pod._mp3_tagger(TestEpisode)
    #     # TODO This works, but I need to automate validation that it does

    # @patch('feedparser.parse')
    # def test_mp4_tagger(self, mock_obj):
    #     class TestEpisode:
    #         filename = path.join(path.join(path.dirname(__file__), 'testfiles'), 'test.m4a')
    #         title = 'test title'
    #         date = datetime.now()
    #     mock_obj.return_value = RYAN
    #     with miscfunctions.Podcast(DATE, DIR_PATH, RYAN_URL, DATABASE) as pod:
    #             pod._mp4_tagger(TestEpisode)
    #     # TODO This works, but I need to automate validation that it does

#
# class TestMessage(unittest.TestCase):
#
#     def setUp(self):
#         pass
#
#     def tearDown(self):
#         pass
#

if __name__ == '__main__':
    unittest.main()