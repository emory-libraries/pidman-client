"""
*"Fail at Love and the other tests don't matter"*

- **Richard Bach**

"""

import os
import unittest

# from django.core.management import setup_environ
from django.conf import settings
settings.configure(
            PIDMAN_HOST = 'http://testpidman.library.emory.edu/',
            PIDMAN_USER = 'testuser',
            PIDMAN_PASSWORD = 'testpass',
)
#os.environ['DJANGO_SETTINGS_MODULE'] = settings

from pidservices.clients import PidmanRestClient
from pidservices.djangowrapper.shortcuts import DjangoPidmanRestClient

class PidmanRestClientTest(unittest.TestCase):

    def setUp(self):
        baseurl = 'http://brutus.library.emory.edu/pidman/'
        username = ''
        password = ''
        self.noauth_client = PidmanRestClient(baseurl, username, password)

    def test_search_pids(self):
        """Tests the REST return for searching pids."""

        data = self.noauth_client.search_pids({})
        # TODO: Change this to a real test when the staging server is udpated
        # to include the rest API code.
        self.assertTrue(data, "No return when trying to search pids!!")

class DjangoPidmanRestClientTest(unittest.TestCase):

     def test_constructor(self):
        client = DjangoPidmanRestClient()
        self.assertEqual(client.baseurl,
            'http://testpidman.library.emory.edu/',
            'Client Base URL %s not expected value.' % client.baseurl)
        self.assertEqual(client.username, 'testuser',
            'Client username %s not the expected value' % client.username)
        self.assertEqual(client.password, 'testpass',
            'Client password %s is not expected value' % client.password)

     def test_runtime_error(self):
        del settings.PIDMAN_HOST
        self.assertRaises(RuntimeError, DjangoPidmanRestClient)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(PidmanRestClientTest("test_search_pids"))
    suite.addTest(DjangoPidmanRestClientTest("test_constructor"))
    suite.addTest(DjangoPidmanRestClientTest("test_runtime_error"))
    return suite

if __name__ == '__main__':
    # Setup our test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
