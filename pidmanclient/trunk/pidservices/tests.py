"""
*"Fail at Love and the other tests don't matter"*
- **Richard Bach**
"""

import unittest

from clients import PidmanRestClient

class PidmanRestClientTest(unittest.TestCase):

    def setUp(self):
        baseurl = 'http://brutus.library.emory.edu/pidman/'
        username = ''
        password = ''
        self.noauth_client = PidmanRestClient(baseurl, username, password)

    def test_search_pids(self):
        """Tests the REST return for searching pids."""

        data = self.noauth_client.search_pids({})
        self.assertFalse(data)

if __name__ == '__main__':
    unittest.main()
