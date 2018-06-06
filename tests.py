from datetime import datetime
from os import listdir, path, remove
import pathlib
import sqlite3
import unittest
from unittest.mock import patch

from database import Database, Feed, create_database
from podcast import Episode, Podcast
from utilities import load_test_objects, logger

DATABASE = path.join(path.dirname(path.abspath(__file__)), 'tests.db')
DATE = datetime(2017, 2, 8, 17, 0)
DIRECTORY = '/path/to/place/files'
HOME = path.join(pathlib.Path.home(), 'Podcasts')
NAME = 'example podcast'
RYAN_URL = 'http://tangent.libsyn.com/rss'
GOLD_URL = 'http://www.goldmansachs.com/exchanges-podcast/feed.rss'
RYAN, GOLD, PETERSON = load_test_objects()
TEST_LOG = path.join(path.join(path.dirname(path.abspath(__file__)), 'Logs'), 'test_logger')
URL = 'examplepodcast.com/feed.rss'


class Setup(unittest.TestCase):
    def setUp(self):
        create_database(DATABASE)

    def tearDown(self):
        remove(DATABASE)


class TestDatabase(Setup):

    def test_database_creation(self):
        remove(DATABASE)  # Since we're testing creation func first, just remove the existing db file
        create_database(DATABASE)
        self.assertIn('tests.db', listdir(path.dirname(__file__)))
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [item[0] for item in cursor.fetchall()]
        self.assertIn('podcasts', tables)
        self.assertIn('episodes', tables)
        self.assertIn('settings', tables)
        for table in tables:
            res = cursor.execute('PRAGMA TABLE_INFO("%s")' % table).fetchall()
            if table == 'podcasts':
                columns = ['id', 'name', 'url', 'directory']
            elif table == 'episodes':
                columns = ['id', 'feed_id', 'podcast_id']
            else:
                columns = ['id', 'new_only', 'download_directory']
            for index, column in enumerate(res):
                name = column[1]
                self.assertEqual(name, columns[index])
        cursor.execute('SELECT * FROM settings WHERE id = 1')
        res = cursor.fetchone()
        self.assertEqual(res, (1, 1, HOME))
        conn.close()

    def test_add_podcast(self):

        with Database(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM main.podcasts WHERE id = 1')
        res = cursor.fetchone()
        self.assertEqual(res, (1, NAME, URL, DIRECTORY))
        with Database(DATABASE) as db:
            with self.assertRaises(sqlite3.IntegrityError):  # Checking that unique constraint is raised
                db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)

    def test_add_episodes(self):
        feed_id = '1234567'
        with Database(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
            db.add_episode(podcast_url=URL,
                           feed_id=feed_id)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM main.episodes WHERE id = 1')
        res = cursor.fetchone()
        self.assertEqual(res, (1, feed_id, 1))

    def test_remove_podcast(self):
        url2 = 'google.com'
        with Database(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
            db.add_podcast(name=NAME, url=url2, directory=DIRECTORY)
            db.add_episode(podcast_url=URL, feed_id='123456')
            db.add_episode(podcast_url=URL, feed_id='512312456')
        with Database(DATABASE) as db:
            db.remove_podcast(url=URL)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * from main.episodes')
        self.assertEqual(0, len([i[0] for i in cursor.fetchall()]))
        cursor.execute('SELECT * from main.podcasts')
        self.assertEqual(1, len([i[0] for i in cursor.fetchall()]))

    def test_get_options(self):
        with Database(DATABASE) as db:
            self.assertEqual((1, HOME), db.get_options())

    def test_set_options(self):
        with Database(DATABASE) as db:
            db.change_option('new_only', '0')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT new_only FROM main.settings WHERE id = 1')
        self.assertEqual(0, cursor.fetchone()[0])

    def test_get_podcasts(self):
        url2 = 'google.com'
        with Database(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
            db.add_podcast(name=NAME, url=url2, directory=DIRECTORY)
            podcasts = db.get_podcasts()
        one, two = podcasts
        self.assertEqual(one, (NAME, URL, DIRECTORY))
        self.assertEqual(two, (NAME, url2, DIRECTORY))

    def test_get_episodes(self):
        url2 = 'google.com'
        with Database(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
            db.add_podcast(name=NAME, url=url2, directory=DIRECTORY)
            db.add_episode(podcast_url=URL, feed_id='123456')
            db.add_episode(podcast_url=URL, feed_id='512312456')
            db.add_episode(podcast_url=URL, feed_id='4')
            db.add_episode(podcast_url=URL, feed_id='5')
            db.add_episode(podcast_url=url2, feed_id='1')
            db.add_episode(podcast_url=url2, feed_id='2')
        with Database(DATABASE) as db:
            db.add_episode(podcast_url=URL, feed_id='6')
            db.add_episode(podcast_url=url2, feed_id='3')
        with Database(DATABASE) as db:
            self.assertEqual(db.get_episodes(URL), {'123456', '512312456', '4', '5', '6'})
            self.assertEqual(db.get_episodes(url2), {'1', '2', '3'})


class TestFeed(Setup):

    def test_add_bad_podcast(self):
        """
        Add some URLs that don't contain a valid rss feed
        :return: None
        """
        with Feed(DATABASE) as feed:
            feed.add('google.com')
            feed.add('yahoo.com')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM main.podcasts')
        res = [i[0] for i in cursor.fetchall()]
        self.assertEqual([], res)

    @patch('feedparser.parse')
    def test_add_good_podcast(self, mock_method):
        mock_method.return_value = GOLD
        with Feed(DATABASE) as feed:
            feed.change_option('new_only', 0)
            feed.add(GOLD_URL)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM episodes')
        res = [i[0] for i in cursor.fetchall()]
        conn.close()
        self.assertEqual(len(res), 0)

    @patch('feedparser.parse')
    def test_add_podcast_with_single_episode(self, mock_method):
        mock_method.return_value = RYAN
        with Feed(DATABASE) as feed:
            feed.change_option('new_only', 1)
            feed.add(RYAN_URL)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM episodes')
        res = cursor.fetchall()
        conn.close()
        self.assertEqual(326, len(res))

    @patch('builtins.input')
    def test_remove_podcasts(self, mock_method):
        """
        This test patches out input to simulate user typing in 1 and pressing return
        , which is how one would remove a podcast from the database
        :param mock_method:
        :return:
        """
        mock_method.return_value = '1'
        url2 = 'google.com'
        with Feed(DATABASE) as db:
            db.add_podcast(name=NAME, url=URL, directory=DIRECTORY)
            db.add_podcast(name=NAME, url=url2, directory=DIRECTORY)
            db.remove()
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM podcasts')
        res = [i[0] for i in cursor.fetchall()]
        self.assertEqual(1, len(res))

    def test_print_options(self):
        with Feed(DATABASE) as feed:
            new_only, dl_dir = feed.print_options()
        self.assertEqual(new_only, 1)
        self.assertEqual(dl_dir, HOME)

    def test_set_dir_option(self):
        with Feed(DATABASE) as feed:
            self.assertTrue(feed.set_directory_option(str(pathlib.Path.home())))
            self.assertFalse(feed.set_directory_option('asdfa'))

    def test_set_catalog_option(self):
        with Feed(DATABASE) as feed:
            res = feed.set_catalog_option('new')
        self.assertTrue(res)
        with Feed(DATABASE) as feed:
            res = feed.set_catalog_option('asdfdd')
        self.assertFalse(res)
        with Feed(DATABASE) as feed:
            res = feed.set_catalog_option('all')
        self.assertTrue(res)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT new_only FROM main.settings')
        res = cursor.fetchone()[0]
        self.assertEqual(res, 0)


class TestLogger(unittest.TestCase):

    def tearDown(self):

        remove(TEST_LOG + '.log')

    def test_logger(self):
        files = listdir(path.dirname(TEST_LOG))
        test_logger = logger('test_logger')
        # Checks that file isn't created until a log entry is created.
        self.assertNotIn('test_logger.log', files)
        test_logger.info('test message!')
        files = listdir(path.dirname(TEST_LOG))
        self.assertIn('test_logger.log', files)
        with open(TEST_LOG + '.log', 'r') as file:
            line = file.read()
        self.assertIn('test message!', line)


class TestPodcast(unittest.TestCase):
    pass


class TestEpisode(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
