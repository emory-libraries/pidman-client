"""
*"Fail at Love and the other tests don't matter"*

- **Richard Bach**

"""

import base64
import json
import os
import unittest
import urllib
import urllib2
from urlparse import parse_qs

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
        Returns a client with a mock connection object for testing.
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

    def test_create_pid(self):
        """Test creating pids."""
        # Test a normal working return.
        client = self._new_client()
        new_purl = 'http://pid.emory.edu/purl'      # fake new PURL to return
        client.connection.response.data = new_purl
        client.connection.response.status = 201
        # minimum required parameters
        domain, target = 'http://pid.emory.edu/domains/1/', 'http://some.url'
        created = client.create_pid('purl', domain, target)
        self.assertEqual(new_purl, created)
        # base url configured for tests is /pidman
        expected, got = '/pidman/purl/', client.connection.url
        self.assertEqual(expected, got,
            'create_pid posts to expected url for new purl; expected %s, got %s' % (expected, got))
        self.assertEqual('POST', client.connection.method)
        # parse post values back into a dictionary - each value is a list
        qs_opts = parse_qs(client.connection.postvalues)
        self.assertEqual(domain, qs_opts['domain'][0],
            'expected domain value set in posted data')
        self.assertEqual(target, qs_opts['target_uri'][0],
            'expected target uri value set in posted data')
        # unspecified parameters should not be set in query string args
        self.assert_('name' not in qs_opts,
            'unspecified parameter (name) not set in posted values')
        self.assert_('external_system_id' not in qs_opts,
            'unspecified parameter (external system) not set in posted values')
        self.assert_('external_system_key' not in qs_opts,
            'unspecified parameter (external system key) not set in posted values')
        self.assert_('policy' not in qs_opts,
            'unspecified parameter (policy) not set in posted values')
        self.assert_('proxy' not in qs_opts,
            'unspecified parameter (proxy) not set in posted values')
        self.assert_('qualifier' not in qs_opts,
            'unspecified parameter (qualifier) not set in posted values')
        
        # all parameters
        name, ext_sys, ext_id, qual = 'my new pid', 'EUCLID', 'ocm1234', 'q'
        policy, proxy = 'Not Guaranteed', 'EZProxy'
        created = client.create_pid('ark', domain, target, name, ext_sys, ext_id,
                                    policy, proxy, qual)
        self.assertEqual(new_purl, created)
        expected, got = '/pidman/ark/', client.connection.url
        self.assertEqual(expected, got,
            'create_pid posts to expected url for new ark; expected %s, got %s' % (expected, got))
        qs_opts = parse_qs(client.connection.postvalues)
        # all optional values should be set in query string
        self.assertEqual(name, qs_opts['name'][0],
            'expected name value set in posted data')
        self.assertEqual(ext_sys, qs_opts['external_system_id'][0],
            'expected external system id value set in posted data')
        self.assertEqual(ext_id, qs_opts['external_system_key'][0],
            'expected external system key value set in posted data')
        self.assertEqual(policy, qs_opts['policy'][0],
            'expected policy value set in posted data')
        self.assertEqual(proxy, qs_opts['proxy'][0],
            'expected proxy value set in posted data')
        self.assertEqual(qual, qs_opts['qualifier'][0],
            'expected qualifier value set in posted data')

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.create_pid, 'faux-pid')

        # shortcut methods
        client.create_purl(domain, target)
        expected, got = '/pidman/purl/', client.connection.url
        self.assertEqual(expected, got,
            'create_purl posts to expected url; expected %s, got %s' % (expected, got))
        client.create_ark(domain, target)
        expected, got = '/pidman/ark/', client.connection.url
        self.assertEqual(expected, got,
            'create_ark posts to expected url; expected %s, got %s' % (expected, got))

        # 400 - bad request
        client.connection.response.status = 400
        self.assertRaises(urllib2.HTTPError, client.create_pid, 'ark', 'domain-2',
                          'http://pid.com/')

    def test_get_pid(self):
        """Test retrieving info about a pid."""
        # Test a normal working return.
        client = self._new_client()
        pid_data = {'domain': 'foo', 'name': 'bar'}
        client.connection.response.data = json.dumps(pid_data)
        client.connection.response.status = 200
        pid_info = client.get_pid('purl', 'aa')
        self.assertEqual(pid_data, pid_info)
        # base url configured for tests is /pidman
        expected, got = '/pidman/purl/aa', client.connection.url
        self.assertEqual(expected, got,
            'get_pid requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('GET', client.connection.method)

        # shortcut methods
        client.get_purl('cc')
        expected, got = '/pidman/purl/cc', client.connection.url
        self.assertEqual(expected, got,
            'get_purl requests expected url; expected %s, got %s' % (expected, got))
        client.get_ark('dd')
        expected, got = '/pidman/ark/dd', client.connection.url
        self.assertEqual(expected, got,
            'get_ark requests expected url; expected %s, got %s' % (expected, got))

        # 404 - pid not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.get_pid, 'ark', 'ee')

    def test_get_target(self):
        """Test retrieving info about a pid target."""
        # Test a normal working return.
        client = self._new_client()
        target_data = {'target_uri': 'http://foo.bar/', 'active': True}
        client.connection.response.data = json.dumps(target_data)
        client.connection.response.status = 200
        target_info = client.get_target('purl', 'aa')
        self.assertEqual(target_data, target_info)
        # base url configured for tests is /pidman
        expected, got = '/pidman/purl/aa/', client.connection.url
        self.assertEqual(expected, got,
            'get_target requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('GET', client.connection.method)

        # target qualifier
        target_info = client.get_target('ark', 'bb', 'PDF')
        expected, got = '/pidman/ark/bb/PDF', client.connection.url
        self.assertEqual(expected, got,
            'get_target requests expected url; expected %s, got %s' % (expected, got))

        # shortcut methods
        client.get_purl_target('cc')
        expected, got = '/pidman/purl/cc/', client.connection.url
        self.assertEqual(expected, got,
            'get_purl_target requests expected url; expected %s, got %s' % (expected, got))
        client.get_ark_target('dd', 'XML')
        expected, got = '/pidman/ark/dd/XML', client.connection.url
        self.assertEqual(expected, got,
            'get_ark_target requests expected url; expected %s, got %s' % (expected, got))

        # 404 - pid not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.get_target, 'ark', 'ee')


# Test the Django wrapper code for pidman Client.
class DjangoPidmanRestClientTest(unittest.TestCase):

     def test_constructor(self):
        'Test init from Django settings.'
        client = DjangoPidmanRestClient()
        self.assertEqual(client.baseurl['host'],
            'testpidman.library.emory.edu',
            'Client Base URL %s not expected value.' % client.baseurl)
        self.assertEqual(client.username, 'testuser',
            'Client username %s not the expected value' % client.username)
        self.assertEqual(client.password, base64.b64encode('testpass'),
            'Client password %s is not expected value' % client.password)

     def test_runtime_error(self):
        'Test Django init without required Django settings'
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
    suite.addTest(PidmanRestClientTest("test_create_pid"))
    suite.addTest(PidmanRestClientTest("test_get_pid"))
    suite.addTest(PidmanRestClientTest("test_get_target"))
    suite.addTest(DjangoPidmanRestClientTest("test_constructor"))
    suite.addTest(DjangoPidmanRestClientTest("test_runtime_error"))
    return suite

if __name__ == '__main__':
    # Setup our test suite
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
