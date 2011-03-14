"""
*"Fail at Love and the other tests don't matter"*

- **Richard Bach**

"""

import httplib
import json
import unittest
import urllib2
from urlparse import parse_qs

# from django.core.management import setup_environ
from django.conf import settings
settings.configure(
            PIDMAN_HOST = 'http://testpidman.library.emory.edu/',
            PIDMAN_USER = 'testuser',
            PIDMAN_PASSWORD = 'testpass',
)

from pidservices.clients import PidmanRestClient, is_ark, parse_ark
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

        # password should base64 encoded in an auth token
        self.assert_('testuserpass' not in client._auth_token,
            'Password has not been encoded!')

        # url with trailing slash - treated same as without
        client = PidmanRestClient('%s/' % self.baseurl)
        self.assertEqual(client.baseurl['path'],
            '/pidman', 
            'Path not correctly set when baseurl specified with trailing slash')

    def test_connection(self):
        'Test that client initializes correct type of http connection for ssl/non-ssl'
        client = PidmanRestClient('http://pid.com/')
        connection = client._get_connection()
        self.assert_(isinstance(connection, httplib.HTTPConnection))
        self.assertFalse(isinstance(connection, httplib.HTTPSConnection))

        client = PidmanRestClient('https://pid.com/')
        connection = client._get_connection()
        self.assert_(isinstance(connection, httplib.HTTPSConnection))

        client = PidmanRestClient('https://pid.com:8000/')
        connection = client._get_connection()
        self.assert_(isinstance(connection, httplib.HTTPSConnection))
    
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
        self.assert_('AUTHORIZATION' not in data_client.connection.headers,
            'auth header is not passed when listing domains')

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
        self.assert_('AUTHORIZATION'  in client.connection.headers,
            'auth header is passed when creating a new domain')
        self.assertEqual('text/plain', client.connection.headers['Accept'],
            'Accept header should be set to text/plain when creating a new domain')

        # This SHOULD thrown an error.
        bad_client = self._new_client()
        self.assertRaises(Exception, bad_client.create_domain, None)

    def test_get_domain(self):
        """Tests the request and return of a single domain."""
        client = self._new_client()
        client.connection.response.data = '[{"id": 25, "name": "domain name"}]'
        domain = client.get_domain(25)
        self.assertEqual(25, domain[0]['id'])
        self.assert_('AUTHORIZATION' not in client.connection.headers,
            'auth header is not passed when accessing a single domain')

    def test_update_domain(self):
        """Tests the update method for a single domain."""
        client = self._new_client()
        client.connection.response.data = '[{"id": 25, "name": "The Updated Domain", "policy": "", "parent": ""}]'
        domain = client.update_domain(25, name='The Updated Domain')
        self.assert_('AUTHORIZATION'  in client.connection.headers,
            'auth header is passed when updating a domain')

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
        self.assert_('AUTHORIZATION' in client.connection.headers,
            'auth header is passed when creating a pid')
        self.assertEqual('text/plain', client.connection.headers['Accept'],
            'Accept header should be set to text/plain when creating a new pid')
        self.assertEqual('application/x-www-form-urlencoded',
            client.connection.headers['Content-type'],
            'content-type should be form-encoded for POST data')
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

        # handle unicode characters in pid titles
        created = client.create_pid('purl', domain, target, u'unicode \u2026 in title')
        self.assert_(created, 'craete_pid succeeds when title contains non-ascii unicode')

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
        self.assertEqual('POST', client.connection.method)
        client.create_ark(domain, target)
        expected, got = '/pidman/ark/', client.connection.url
        self.assertEqual(expected, got,
            'create_ark posts to expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('POST', client.connection.method)

        # 400 - bad request
        client.connection.response.status = 400
        # when response has body text, should be included in error
        # (can't figure out how to test this in python 2.6; use assertRaisesRegex in 2.7)
        client.connection.response.data = 'Error: Could not resolve domain URI'
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
        self.assert_('AUTHORIZATION' not in client.connection.headers,
            'auth header is passed when accessing a pid')

        # shortcut methods
        client.get_purl('cc')
        expected, got = '/pidman/purl/cc', client.connection.url
        self.assertEqual(expected, got,
            'get_purl requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('GET', client.connection.method)
        client.get_ark('dd')
        expected, got = '/pidman/ark/dd', client.connection.url
        self.assertEqual(expected, got,
            'get_ark requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('GET', client.connection.method)

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
        self.assert_('AUTHORIZATION' not in client.connection.headers,
            'auth header is not passed when accessing a target')

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
        self.assertEqual('GET', client.connection.method)
        client.get_ark_target('dd', 'XML')
        expected, got = '/pidman/ark/dd/XML', client.connection.url
        self.assertEqual(expected, got,
            'get_ark_target requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('GET', client.connection.method)

        # 404 - target not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.get_target, 'ark', 'ee')

    def test_update_pid(self):
        """Test updating an existing pid."""
        # Test a normal working return.
        client = self._new_client()
        pid_info = {'pid': 'foo'}
        client.connection.response.data = json.dumps(pid_info)
        client.connection.response.status = 200
        # minimum required parameters
        pid = client.update_pid('purl', 'aa', name='new name')
        self.assertEqual(pid, pid_info)
        # base url configured for tests is /pidman
        expected, got = '/pidman/purl/aa', client.connection.url
        self.assertEqual(expected, got,
            'update_pid requested expected url for update purl; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)
        self.assert_('AUTHORIZATION' in client.connection.headers,
            'auth header is passed when updating a pid')
        self.assertEqual('application/json', client.connection.headers['Content-type'],
            'content-type should be JSON for PUT data')
        # request body is JSON-encoded update values
        opts = json.loads(client.connection.postvalues)
        self.assertEqual('new name', opts['name'],
            'requested new name value set in request data')
        # unspecified parameters should not be set in posted data
        self.assert_('domain' not in opts,
            'unspecified parameter (domain) not set in posted values')
        self.assert_('external_system_id' not in opts,
            'unspecified parameter (external system) not set in posted values')
        self.assert_('external_system_key' not in opts,
            'unspecified parameter (external system key) not set in posted values')
        self.assert_('policy' not in opts,
            'unspecified parameter (policy) not set in posted values')

        # all parameters
        domain = 'http://pid.emory.edu/domains/1/'
        name, ext_sys, ext_id = 'my new pid', 'EUCLID', 'ocm1234'
        policy = 'Not Guaranteed'
        pid = client.update_pid('ark', 'bb', domain, name, ext_sys,
                                    ext_id, policy)
        expected, got = '/pidman/ark/bb', client.connection.url
        self.assertEqual(expected, got,
            'update_pid requests to expected url for new ark; expected %s, got %s' % (expected, got))
        opts = json.loads(client.connection.postvalues)
        # all optional values should be set in query string
        self.assertEqual(domain, opts['domain'],
            'expected domain value set in posted data')
        self.assertEqual(ext_sys, opts['external_system_id'],
            'expected external system id value set in posted data')
        self.assertEqual(ext_id, opts['external_system_key'],
            'expected external system key value set in posted data')
        self.assertEqual(policy, opts['policy'],
            'expected policy value set in posted data')

        # empty values are valid - e.g., blank out previous value
        pid = client.update_pid('ark', 'bb', domain='', name='')
        opts = json.loads(client.connection.postvalues)
        # all optional values should be set in query string
        self.assertEqual('', opts['domain'],
            'expected domain value set in posted data')
        self.assertEqual('', opts['name'],
            'expected name value set in posted data')

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.update_pid, 'faux-pid')

        # shortcut methods
        client.update_purl('aa', domain, name)
        expected, got = '/pidman/purl/aa', client.connection.url
        self.assertEqual(expected, got,
            'update_purl requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)
        client.update_ark('bb', domain, name)
        expected, got = '/pidman/ark/bb', client.connection.url
        self.assertEqual(expected, got,
            'update_ark requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)

        # 404 - pid not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.update_pid, 'ark', 'ee', 'domain')


    def test_update_target(self):
        """Test updating an existing target."""
        # Test a normal working return.
        client = self._new_client()
        target_info = {'target_uri': 'http://foo.bar/'}
        client.connection.response.data = json.dumps(target_info)
        client.connection.response.status = 200
        # minimum required parameters
        target = client.update_target('purl', 'aa', active=False)
        self.assertEqual(target, target_info)
        # base url configured for tests is /pidman
        expected, got = '/pidman/purl/aa/', client.connection.url
        self.assertEqual(expected, got,
            'update_target requested expected url for update purl target; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)
        self.assert_('AUTHORIZATION' in client.connection.headers,
            'auth header is passed when updating a target')
        # request body is JSON-encoded update values
        opts = json.loads(client.connection.postvalues)
        self.assertEqual(False, opts['active'],
            'update active value set in request data')
        # unspecified parameters should not be set in posted data
        self.assert_('target_uri' not in opts,
            'unspecified parameter (target_uri) not set in update values')
        self.assert_('proxy' not in opts,
            'unspecified parameter (proxy) not set in update values')

        # all parameters
        target, proxy, active = 'http://pid.com', 'MyProxy', True
        client.update_target('ark', 'bb', 'PDF', target, proxy, active)
        expected, got = '/pidman/ark/bb/PDF', client.connection.url
        self.assertEqual(expected, got,
            'update_target requests expected url for ark target; expected %s, got %s' % (expected, got))
        opts = json.loads(client.connection.postvalues)
        # all optional values should be set in query string
        self.assertEqual(target, opts['target_uri'],
            'expected target value set in update data')
        self.assertEqual(proxy, opts['proxy'],
            'expected proxy value set in update data')
        self.assertEqual(active, opts['active'],
            'expected active value set in update data')

        # empty values are valid - e.g., blank out previous value
        client.update_target('ark', 'bb', 'XML', target_uri='', proxy='')
        opts = json.loads(client.connection.postvalues)
        # all optional values should be set in query string
        self.assertEqual('', opts['target_uri'],
            'expected target value set in posted data')
        self.assertEqual('', opts['proxy'],
            'expected proxy value set in posted data')

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.update_target, 'faux-pid', 'bb')

        # shortcut methods
        client.update_purl_target('aa', target, proxy)
        expected, got = '/pidman/purl/aa/', client.connection.url
        self.assertEqual(expected, got,
            'update_purl_target requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)
        client.update_ark_target('bb', 'PDF', target_uri=target, proxy=proxy)
        expected, got = '/pidman/ark/bb/PDF', client.connection.url
        self.assertEqual(expected, got,
            'update_ark_target requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)
        # can actually create a *new* ark target using update - returns 201
        client.connection.response.status = 201
        client.update_ark_target('bb', 'NEW-qual', target_uri=target)
        expected, got = '/pidman/ark/bb/NEW-qual', client.connection.url
        self.assertEqual(expected, got,
            'update_ark_target requests expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('PUT', client.connection.method)

        # 404 - target not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.update_target, 'ark', 'ee', active=False)

    def test_delete_target(self):
        """Test deleting an existing target."""
        # Test a normal working return.
        client = self._new_client()
        client.connection.response.status = 200
        deleted = client.delete_ark_target('aa')
        self.assertTrue(deleted, 'delete_ark_target returns True on successul delete')
        # base url configured for tests is /pidman
        expected, got = '/pidman/ark/aa/', client.connection.url
        self.assertEqual(expected, got,
            'delete_target requested expected url; expected %s, got %s' % (expected, got))
        self.assertEqual('DELETE', client.connection.method)
        self.assert_('AUTHORIZATION' in client.connection.headers,
            'auth header is passed when deleting a target')

        # 404 - target not found
        client.connection.response.status = 404
        self.assertRaises(urllib2.HTTPError, client.delete_ark_target, 'ee', 'pdf')


# Test the Django wrapper code for pidman Client.
class DjangoPidmanRestClientTest(unittest.TestCase):

     def test_constructor(self):
        'Test init from Django settings.'
        client = DjangoPidmanRestClient()
        self.assertEqual(client.baseurl['host'],
            'testpidman.library.emory.edu',
            'Client Base URL %s not expected value.' % client.baseurl)
            
        # credentials are used to generate a Basic Auth token
        # reverse the Basic Auth header construction to confirm expected values
        basic_auth = client._auth_token[len('Basic '):]
        username, password = basic_auth.decode('base64').split(':')
        self.assertEqual(username, 'testuser',
            'Client username %s not the expected value' % username)
        self.assertEqual(password, 'testpass',
            'Client password %s is not expected value' % password)

     def test_runtime_error(self):
        'Test Django init without required Django settings'
        del settings.PIDMAN_HOST
        self.assertRaises(RuntimeError, DjangoPidmanRestClient)



class IsArkTest(unittest.TestCase):

    def test_is_ark(self):
        'Test is_ark method'
        # resolvable ark
        self.assertTrue(is_ark('http://pid.emory.edu/ark:/25593/1fx'))
        # resolvable arks with qualifier
        self.assertTrue(is_ark('http://pid.emory.edu/ark:/25593/1fx/qual'))
        self.assertTrue(is_ark('http://pid.emory.edu/ark:/25593/1fx/qual/1.23/foo-bar'))
        # resolvable ark with base path in url
        self.assertTrue(is_ark('http://test.site.com/pidman/ark:/25593/1fx/qual'))

        # short-form ark
        self.assertTrue(is_ark('ark:/25593/1fx'))
        # short-form arks with qualifier
        self.assertTrue(is_ark('ark:/25593/1fx/qual'))
        self.assertTrue(is_ark('ark:/25593/1fx/qual/1.23/foo-bar'))

        # non-arks
        self.assertFalse(is_ark('http://pid.emory.edu/'))
        self.assertFalse(is_ark('http://genes.is/noahs/ark'))
        self.assertFalse(is_ark('http://pid.emory.edu/'))
        self.assertFalse(is_ark('http://genes.is/noahs/ark'))
        self.assertFalse(is_ark('doi:10.1000/182'))

class ParseArkTest(unittest.TestCase):
    def test_parse_ark(self):
        'Test parse_ark method'

        # use these strings to construct various versions of valid arks
        # and confirm they are returned properly from the parse_ark method
        ark_parts = {
            'nma': 'http://pid.emory.edu/',
            'naan': '25593',
            'noid': '1fx',
            'qual': 'qual/1.23/foo-bar.baz'
        }

        # unqualified resolvable ark
        parsed_ark = parse_ark('%(nma)sark:/%(naan)s/%(noid)s' % ark_parts)
        self.assertEqual(ark_parts['nma'], parsed_ark['nma'])
        self.assertEqual(ark_parts['naan'], parsed_ark['naan'])
        self.assertEqual(ark_parts['noid'], parsed_ark['noid'])
        self.assertEqual(None, parsed_ark['qualifier'])     # not present

        # qualified resolvable ark
        parsed_ark = parse_ark('%(nma)sark:/%(naan)s/%(noid)s/%(qual)s' % ark_parts)
        self.assertEqual(ark_parts['nma'], parsed_ark['nma'])
        self.assertEqual(ark_parts['naan'], parsed_ark['naan'])
        self.assertEqual(ark_parts['noid'], parsed_ark['noid'])
        self.assertEqual(ark_parts['qual'], parsed_ark['qualifier'])  

        # short-form ark
        parsed_ark = parse_ark('ark:/%(naan)s/%(noid)s' % ark_parts)
        self.assertEqual(None, parsed_ark['nma'])   # not present
        self.assertEqual(ark_parts['naan'], parsed_ark['naan'])
        self.assertEqual(ark_parts['noid'], parsed_ark['noid'])
        self.assertEqual(None, parsed_ark['qualifier'])

        # short-form ark with qualifier
        parsed_ark = parse_ark('ark:/%(naan)s/%(noid)s/%(qual)s' % ark_parts)
        self.assertEqual(None, parsed_ark['nma'])   # not present
        self.assertEqual(ark_parts['naan'], parsed_ark['naan'])
        self.assertEqual(ark_parts['noid'], parsed_ark['noid'])
        self.assertEqual(ark_parts['qual'], parsed_ark['qualifier'])

        # non-arks
        self.assertEqual(None, parse_ark('doi:10.1000/182'),
            'attempting to parse non-ark results in None')

def suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    test_cases = (
        PidmanRestClientTest,
        DjangoPidmanRestClientTest,
        IsArkTest,
        ParseArkTest,
    )
    for test_case in test_cases:
        suite.addTests(loader.loadTestsFromTestCase(test_case))
        
    return suite

if __name__ == '__main__':
    # Setup our test suite
    testrunner = unittest.TextTestRunner(verbosity=2)
    try:
        # use xmlrunner when available for detailed error reports in hudson
        import xmlrunner
        testrunner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    testrunner.run(suite())

