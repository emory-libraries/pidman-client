"""
*"Fail at Love and the other tests don't matter"*

- **Richard Bach**

"""

import os, unittest, base64, json, urllib2

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

# Mock httplib so we don't need an actual server to test against.
class MockHttpResponse():

    def __init__(self):
        self.status = 200
        self.reason = "this is my reason"
        self.data = None

    def set_data(self, data):
        """
        Sets the data expected in the return.
        """
        self.data = data

    def set_status(self, code):
        self.status = code

    def read(self):
        """Returns the data as per a read."""
        return self.data

class MockHttpConnection():

    def __init__(self):
        self.response = MockHttpResponse()

    def request(self, method, url, postvalues, headers):
        self.method = method
        self.url = url
        self.postvalues = postvalues
        self.headers = headers
        
    def getresponse(self):
        return self.response

    def close(self):
        pass

class MockHttplib:

    def __init__(self, url):
        self.url = url
        self.connection = MockHttpConnection()

# Test the normal pidman client.

class PidmanRestClientTest(unittest.TestCase):

    def setUp(self):
        self.baseurl = 'http://brutus.library.emory.edu/pidman'
        self.username = 'testuser'
        self.password = 'testuserpass'

    def _new_client(self):
        """
        Returns a client with a mock connectin object for testing.
        """
        client = PidmanRestClient(self.baseurl, self.username, self.password)
        mock = MockHttplib(client.baseurl['host'])
        client.connection = mock.connection # Replace the normal connection for testing.
        return client

    def test_constructor(self):
        """Tests the proper constructor values are set"""
        client = self._new_client()
        self.assertEqual(client.baseurl['scheme'],
            'http', 'Scheme not set to http as spected for baseurl!')
        self.assertEqual(client.baseurl['host'],
            'brutus.library.emory.edu', 'Host not correctly set for baseurl!')
        self.assertEqual(client.baseurl['path'],
            '/pidman', 'Path not correctly set for baseurl!')
        self.assertNotEqual(client.password, 'testuserpass',
            'Password has not been encoded!')

    def test_search_pids(self):
        """Tests the REST return for searching pids."""
        # Be a normal return.
        norm_client = self._new_client()
        norm_client.connection.response.data = '[{"pid": "testblank"}]'
        data = norm_client.search_pids({})
        self.assertTrue(data, "No return when trying to search pids!!")

        # This shoule error
        bad_client = self._new_client()
        bad_client.connection.response.set_status(201)
        self.assertRaises(urllib2.HTTPError, bad_client.search_pids)

    def test_list_domains(self):
        """Tests the REST list domain method."""
        data_client = self._new_client()
        data_client.connection.response.data = '[{"pid": "testblank"}]'
        data = data_client.list_domains()
        self.assertTrue(data, "No data returned when listing domains.")

        # This shoule error
        bad_client = self._new_client()
        bad_client.connection.response.set_status(201)
        self.assertRaises(urllib2.HTTPError, bad_client.search_pids)

    def test_create_domain(self):
        """Tests the creation of the domain."""
        # Test a normal working return.
        client = self._new_client()
        client.connection.response.data = ''
        client.connection.response.status = 201
        client.create_domain('Test Domain')
        # I'm actually just testing that this doesn't throw an error.
        self.assertEqual(201, client.connection.response.status)

        # This SHOULD thrown an error.
        bad_client = self._new_client()
        self.assertRaises(Exception, bad_client.create_domain, None)

    def test_request_domain(self):
        """Tests the request and return of a single domain."""
        client = self._new_client()
        client.connection.response.data = '[{"id": 25, "name": "domain name"}]'
        domain = client.request_domain(25)
        self.assertEqual(25, domain[0]['id'])

    def test_update_domain(self):
        """Tests the update method for a single domain."""
        client = self._new_client()
        client.connection.response.data = '[{"id": 25, "name": "The Updated Domain", "policy": "", "parent": ""}]'
        domain = client.update_domain(25, name='The Updated Domain')

        # Test a normal response to ensure it's giving back a pythonic object.
        self.assertEqual(200, client.connection.response.status) # Check the Return
        self.assertEqual('The Updated Domain', domain[0]['name'], "Domain not parsed as expected!")

        # Make sure it throws an error if passed no Data.
        client.connection.response.data = ''
        self.assertRaises(urllib2.HTTPError, client.update_domain, 25)

        # Make sure it returns other errors if returned by server.
        client.connection.response.data = '[{"id": 25, "name": "The Updated Domain", "policy": "", "parent": ""}]'
        client.connection.response.status = 500
        self.assertRaises(urllib2.HTTPError, client.update_domain, 25, name="The Updated Domain")


# Test the Django wrapper code for pidman Client.
class DjangoPidmanRestClientTest(unittest.TestCase):

     def test_constructor(self):
        client = DjangoPidmanRestClient()
        self.assertEqual(client.baseurl['host'],
            'testpidman.library.emory.edu',
            'Client Base URL %s not expected value.' % client.baseurl)
        self.assertEqual(client.username, 'testuser',
            'Client username %s not the expected value' % client.username)
        self.assertEqual(client.password, base64.b64encode('testpass'),
            'Client password %s is not expected value' % client.password)

     def test_runtime_error(self):
        del settings.PIDMAN_HOST
        self.assertRaises(RuntimeError, DjangoPidmanRestClient)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(PidmanRestClientTest("test_search_pids"))
    suite.addTest(PidmanRestClientTest("test_constructor"))
    suite.addTest(PidmanRestClientTest("test_list_domains"))
    suite.addTest(PidmanRestClientTest("test_create_domain"))
    suite.addTest(PidmanRestClientTest("test_request_domain"))
    suite.addTest(PidmanRestClientTest("test_update_domain"))
    suite.addTest(DjangoPidmanRestClientTest("test_constructor"))
    suite.addTest(DjangoPidmanRestClientTest("test_runtime_error"))
    return suite

if __name__ == '__main__':
    # Setup our test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
