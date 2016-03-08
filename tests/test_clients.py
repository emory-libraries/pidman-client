"""
*"Fail at Love and the other tests don't matter"*

- **Richard Bach**

"""

import json
import unittest
from mock import patch, MagicMock
import requests

# from django.core.management import setup_environ
from django.conf import settings
settings.configure(
    PIDMAN_HOST='http://testpidman.library.emory.edu/',
    PIDMAN_USER='testuser',
    PIDMAN_PASSWORD='testpass',
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

        # mock helper method for make request, which uses method name for logging
        self.mock_get = MagicMock(__name__='get')
        self.mock_post = MagicMock(__name__='post')
        self.mock_put = MagicMock(__name__='put')
        self.mock_delete = MagicMock(__name__='delete')
        for mockmeth in [self.mock_get, self.mock_post, self.mock_put, self.mock_delete]:
            mockmeth.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError

    def _new_client(self):
        """
        Initialize client with configured settings for testing.
        """
        return PidmanRestClient(self.baseurl, self.username, self.password)

    def test_constructor(self):
        """Tests the proper constructor values are set"""
        client = self._new_client()
        self.assertEqual(client.baseurl['scheme'],
            'http', 'Scheme not set to http as spected for baseurl!')
        self.assertEqual(client.baseurl['host'],
            'brutus.library.emory.edu', 'Host not correctly set for baseurl!')
        self.assertEqual(client.baseurl['path'],
            '/pidman', 'Path not correctly set for baseurl!')

        # url with trailing slash - treated same as without
        client = PidmanRestClient('%s/' % self.baseurl)
        self.assertEqual(client.baseurl['path'],
            '/pidman',
            'Path not correctly set when baseurl specified with trailing slash')

    def test_search_pids(self):
        """Tests the REST return for searching pids."""
        # Be a normal return.
        norm_client = self._new_client()
        with patch.object(norm_client, 'session') as mocksession:
            mocksession.get = self.mock_get
            self.mock_get.return_value.json.return_value = {"pid": "testblank"}
            self.mock_get.return_value.status_code = requests.codes.ok
            data = norm_client.search_pids()
            self.assertTrue(data, "No return when trying to search pids!!")
            # TODO: inspect request parameters?

        # This shoule error
        bad_client = self._new_client()
        with patch.object(bad_client, 'session') as mocksession:
            mocksession.get = self.mock_get
            self.mock_get.return_value.status_code = requests.codes.bad_request
            # bad_client.connection.response.set_status(400)
            self.assertRaises(requests.exceptions.HTTPError, bad_client.search_pids)

    def test_list_domains(self):
        """Tests the REST list domain method."""
        data_client = self._new_client()
        with patch.object(data_client, 'session') as mocksession:
            mocksession.get = self.mock_get
            self.mock_get.return_value.json.return_value = {"pid": "testblank"}
            self.mock_get.return_value.status_code = requests.codes.ok
            data = data_client.list_domains()
            self.assertTrue(data, "No data returned when listing domains.")
            call_args = self.mock_get.call_args
            self.assert_('auth' not in call_args,
                'authentication should not be passed when listing domains')

        # This should error
        bad_client = self._new_client()
        with patch.object(bad_client, 'session') as mocksession:
            mocksession.get = self.mock_get
            self.mock_get.return_value.status_code = requests.codes.server_error
            self.assertRaises(requests.exceptions.HTTPError, bad_client.search_pids)

    def test_create_domain(self):
        """Tests the creation of the domain."""
        # Test a normal working return.
        client = self._new_client()
        with patch.object(client, 'session') as mocksession:
            mocksession.post = self.mock_post
            response = self.mock_post.return_value
            response.content = ''
            response.status_code = requests.codes.created
            client.create_domain('Test Domain')
            # I'm actually just testing that this doesn't throw an error.
            args, kwargs = self.mock_post.call_args
            self.assert_('auth' in kwargs,
                'authentication should be passed when creating a new domain')
            self.assertEqual('text/plain', kwargs['headers']['Accept'],
                'Accept header should be set to text/plain when creating a new domain')

        # This SHOULD thrown an error.
        bad_client = self._new_client()
        self.assertRaises(Exception, bad_client.create_domain, None)

    def test_get_domain(self):
        """Tests the request and return of a single domain."""
        client = self._new_client()
        with patch.object(client, 'session') as mocksession:
            mocksession.get = self.mock_get
            self.mock_get.return_value.status_code = requests.codes.ok
            self.mock_get.return_value.json.return_value = [{"id": 25, "name": "domain name"}]
            domain = client.get_domain(25)
            self.assertEqual(25, domain[0]['id'])

    def test_update_domain(self):
        """Tests the update method for a single domain."""
        client = self._new_client()
        with patch.object(client, 'session') as mocksession:
            mocksession.put = self.mock_put
            self.mock_put.return_value.json.return_value = {
                "id": 25,
                "name": "The Updated Domain",
                "policy": "", "parent": ""
            }
            self.mock_put.return_value.status_code = requests.codes.ok
            domain_id = 25
            name = 'The Updated Domain'
            domain = client.update_domain(domain_id, name=name)
            args, kwargs = self.mock_put.call_args
            self.assert_('auth' in kwargs,
                'auth header is passed when updating a domain')
            self.assertEqual(name, json.loads(kwargs['data'])['name'])

            # Test a normal response to ensure it's giving back a pythonic object.
            self.assertEqual('The Updated Domain', domain['name'],
                "Domain not parsed as expected!")

            # Make sure it throws an error if passed no data.
            self.assertRaises(Exception, client.update_domain, 25)

            # Make sure it returns other errors if returned by server.
            self.mock_put.return_value.status_code = 500
            self.assertRaises(requests.exceptions.HTTPError, client.update_domain,
                              25, name="The Updated Domain")

    def test_create_pid(self):
        """Test creating pids."""
        # Test a normal working return.
        client = self._new_client()
        new_purl = 'http://pid.emory.edu/purl'      # fake new PURL to return
        with patch.object(client, 'session') as mocksession:
            mocksession.post = self.mock_post
            response = self.mock_post.return_value
            response.content = new_purl
            response.status_code = requests.codes.created

            # minimum required parameters
            domain, target = 'http://pid.emory.edu/domains/1/', 'http://some.url'
            created = client.create_pid('purl', domain, target)
            self.assertEqual(new_purl, created)

            args, kwargs = self.mock_post.call_args
            url = args[0]
            self.assert_(url.endswith('/purl/'),
                'create_pid posts to expected url for new purl; should end with /purl/')

            self.assert_('auth' in kwargs,
                        'auth header is passed when creating a pid')
            self.assertEqual('text/plain', kwargs['headers']['Accept'],
                'Accept header should be set to text/plain when creating a new pid')
            self.assertEqual('application/x-www-form-urlencoded',
                kwargs['headers']['Content-type'],
                'content-type should be form-encoded for POST data')

            params = kwargs['data']
            self.assertEqual(domain, params['domain'],
                'expected domain value set in posted data')
            self.assertEqual(target, params['target_uri'],
                'expected target uri value set in posted data')
            # unspecified parameters should not be set in request
            self.assert_('name' not in params,
                'unspecified parameter (name) not set in posted values')
            self.assert_('external_system_id' not in params,
                'unspecified parameter (external system) not set in posted values')
            self.assert_('external_system_key' not in params,
                'unspecified parameter (external system key) not set in posted values')
            self.assert_('policy' not in params,
                'unspecified parameter (policy) not set in posted values')
            self.assert_('proxy' not in params,
                'unspecified parameter (proxy) not set in posted values')
            self.assert_('qualifier' not in params,
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
            args, kwargs = self.mock_post.call_args

            url = args[0]
            self.assert_(url.endswith('/ark/'),
                'create_pid posts to expected url for new ark; should end with /ark/')

            args, kwargs = self.mock_post.call_args
            # all optional values should be set in request body
            params = kwargs['data']
            self.assertEqual(name, params['name'],
                'expected name value set in posted data')
            self.assertEqual(ext_sys, params['external_system_id'],
                'expected external system id value set in posted data')
            self.assertEqual(ext_id, params['external_system_key'],
                'expected external system key value set in posted data')
            self.assertEqual(policy, params['policy'],
                'expected policy value set in posted data')
            self.assertEqual(proxy, params['proxy'],
                'expected proxy value set in posted data')
            self.assertEqual(qual, params['qualifier'],
                'expected qualifier value set in posted data')

            # 400 - bad request
            self.mock_post.return_value.status_code = requests.codes.bad_request
            # when response has body text, should be included in error
            # (can't figure out how to test this in python 2.6; use assertRaisesRegex in 2.7)
            self.mock_post.return_value.content = 'Error: Could not resolve domain URI'
            self.assertRaises(requests.exceptions.HTTPError, client.create_pid, 'ark', 'domain-2',
                            'http://pid.com/')

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.create_pid, 'faux-pid')

        # shortcut methods
        with patch.object(client, 'create_pid') as mockcreate_pid:
            client.create_purl(domain, target)
            mockcreate_pid.assert_called_with('purl', domain, target)

            client.create_ark(domain, target)
            mockcreate_pid.assert_called_with('ark', domain, target)

    def test_get_pid(self):
        """Test retrieving info about a pid."""
        # Test a normal working return.
        client = self._new_client()
        pid_data = {'domain': 'foo', 'name': 'bar'}
        with patch.object(client, 'session') as mocksession:
            mocksession.get = self.mock_get
            response = self.mock_get.return_value
            response.json.return_value = pid_data
            response.status_code = requests.codes.ok  # 200
            pid_info = client.get_pid('purl', 'aa')
            self.assertEqual(pid_data, pid_info)

            args, kwargs = self.mock_get.call_args
            url = args[0]
            self.assert_(url.endswith('/purl/aa'),
                'get_pid requests expected url; should end with /purl/aa')

            # 404 - pid not found
            response.status_code = requests.codes.not_found
            self.assertRaises(requests.exceptions.HTTPError, client.get_pid, 'ark', 'ee')

        # shortcut methods
        with patch.object(client, 'get_pid') as mockget_pid:
            client.get_purl('cc')
            mockget_pid.assert_called_with('purl', 'cc')

            client.get_ark('dd')
            mockget_pid.assert_called_with('ark', 'dd')


    def test_get_target(self):
        """Test retrieving info about a pid target."""
        # Test a normal working return.
        client = self._new_client()
        target_data = {'target_uri': 'http://foo.bar/', 'active': True}
        with patch.object(client, 'session') as mocksession:
            mocksession.get = self.mock_get
            response = self.mock_get.return_value
            response.json.return_value = target_data
            response.status_code = requests.codes.ok # 200
            target_info = client.get_target('purl', 'aa')
            self.assertEqual(target_data, target_info)
            args, kwargs = self.mock_get.call_args
            # expected, got = '/pidman/purl/aa/', client.connection.url
            url = args[0]
            self.assert_(url.endswith('/purl/aa/'),
                'get_target requests expected url; should end with /purl/aa/')

            self.assert_('auth' not in kwargs,
                'auth header is not passed when accessing a target')

            # target qualifier
            target_info = client.get_target('ark', 'bb', 'PDF')
            args, kwargs = self.mock_get.call_args
            url = args[0]
            self.assert_(url.endswith('/ark/bb/PDF'),
                'get_target requests expected url; should end with /ark/bb/PDF')

            # 404 - target not found
            response.status_code = requests.codes.not_found # 404
            self.assertRaises(requests.exceptions.HTTPError, client.get_target, 'ark', 'ee')

        # shortcut methods
        with patch.object(client, 'get_target') as mockget_target:
            client.get_purl_target('cc')
            mockget_target.assert_called_with('purl', 'cc')

            client.get_ark_target('dd', 'XML')
            mockget_target.assert_called_with('ark', 'dd', 'XML')


    def test_update_pid(self):
        """Test updating an existing pid."""
        # Test a normal working return.
        client = self._new_client()
        pid_info = {'pid': 'foo'}
        with patch.object(client, 'session') as mocksession:
            mocksession.put = self.mock_put
            response = self.mock_put.return_value
            response.json.return_value = pid_info
            response.status_code = requests.codes.ok # 200

            # minimum required parameters
            pid = client.update_pid('purl', 'aa', name='new name')
            self.assertEqual(pid, pid_info)

            # base url configured for tests is /pidman
            args, kwargs = self.mock_put.call_args
            # expected, got = '/pidman/purl/aa', client.connection.url
            url = args[0]
            self.assert_(url.endswith('/purl/aa'),
                'update_pid requested expected url for update purl; should end with /purl/aa')
            self.assert_(kwargs['auth'],
                'auth header is passed when updating a pid')
            self.assertEqual('application/json', kwargs['headers']['Content-type'],
                'content-type should be JSON for PUT data')
            # request body is JSON-encoded update values
            opts = json.loads(kwargs['data'])
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
            args, kwargs = self.mock_put.call_args
            url = args[0]
            self.assert_(url.endswith('/ark/bb'),
                'update_pid requests to expected url for new ark; should end with /ark/bb')
            opts = json.loads(kwargs['data'])
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
            args, kwargs = self.mock_put.call_args
            opts = json.loads(kwargs['data'])
            # all optional values should be set in query string
            self.assertEqual('', opts['domain'],
                'expected domain value set in posted data')
            self.assertEqual('', opts['name'],
                'expected name value set in posted data')

            # 404 - pid not found
            response.status_code = requests.codes.not_found # 404
            self.assertRaises(requests.exceptions.HTTPError, client.update_pid, 'ark', 'ee', 'domain')

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.update_pid, 'faux-pid')

        # shortcut methods
        with patch.object(client, 'update_pid') as mockupdate_pid:
            client.update_purl('aa', domain, name)
            mockupdate_pid.assert_called_with('purl', 'aa', domain, name)

            client.update_ark('bb', domain, name)
            mockupdate_pid.assert_called_with('ark', 'bb', domain, name)

    def test_update_target(self):
        """Test updating an existing target."""
        # Test a normal working return.
        client = self._new_client()
        target_info = {'target_uri': 'http://foo.bar/'}
        with patch.object(client, 'session') as mocksession:
            mocksession.put = self.mock_put
            response = self.mock_put.return_value
            response.json.return_value = target_info
            response.status_code = requests.codes.ok # 200

            # minimum required parameters
            target = client.update_target('purl', 'aa', active=False)
            self.assertEqual(target, target_info)

            # base url configured for tests is /pidman
            args, kwargs = self.mock_put.call_args
            url = args[0]
            self.assert_(url.endswith('/purl/aa/'),
                'update_target url for update purl target should end with "/purl/aa/"')
            self.assert_(kwargs['auth'],
                'auth header is passed when updating a target')

            # request body is JSON-encoded update values
            opts = json.loads(kwargs['data'])
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
            args, kwargs = self.mock_put.call_args
            url = args[0]
            self.assert_(url.endswith('ark/bb/PDF'),
                'update_target url for ark target should end with ark/bb/PDF')

            opts = json.loads(kwargs['data'])
            # all optional values should be set in query string
            self.assertEqual(target, opts['target_uri'],
                'expected target value set in update data')
            self.assertEqual(proxy, opts['proxy'],
                'expected proxy value set in update data')
            self.assertEqual(active, opts['active'],
                'expected active value set in update data')

            # empty values are valid - e.g., blank out previous value
            client.update_target('ark', 'bb', 'XML', target_uri='', proxy='')
            args, kwargs = self.mock_put.call_args
            opts = json.loads(kwargs['data'])
            # all optional values should be set in query string
            self.assertEqual('', opts['target_uri'],
                'expected target value set in posted data')
            self.assertEqual('', opts['proxy'],
                'expected proxy value set in posted data')

            # 404 - target not found
            response.status_code = requests.codes.not_found
            self.assertRaises(requests.exceptions.HTTPError, client.update_target, 'ark', 'ee', active=False)

        # invalid pid type should cause an exception
        self.assertRaises(Exception, client.update_target, 'faux-pid', 'bb')

        # shortcut methods
        with patch.object(client, 'update_target') as mockupdate_target:
            client.update_purl_target('aa', target, proxy)
            # '' = empty qualifier
            mockupdate_target.assert_called_with('purl', 'aa', '', target, proxy)

            client.update_ark_target('bb', 'NEW-qual', target_uri=target)
            mockupdate_target.assert_called_with('ark', 'bb', 'NEW-qual', target_uri=target)

    def test_delete_target(self):
        """Test deleting an existing target."""
        # Test a normal working return.
        client = self._new_client()
        with patch.object(client, 'session') as mocksession:
            mocksession.delete = self.mock_delete
            self.mock_delete.return_value.status_code = requests.codes.ok # 200
            deleted = client.delete_ark_target('aa')
            self.assertTrue(deleted, 'delete_ark_target returns True on successul delete')
            # base url configured for tests is /pidman
            args, kwargs = self.mock_delete.call_args
            url = args[0]
            self.assert_(url.endswith('/ark/aa/'),
                'delete_target url should end with /ark/aa/')

            self.assert_('auth' in kwargs,
                'auth header is passed when deleting a target')

            # 404 - target not found
            self.mock_delete.return_value.status_code = requests.codes.not_found # 404
            self.mock_delete.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError
            self.assertRaises(requests.exceptions.HTTPError, client.delete_ark_target, 'ee', 'pdf')


# Test the Django wrapper code for pidman Client.
class DjangoPidmanRestClientTest(unittest.TestCase):

     def test_constructor(self):
        'Test init from Django settings.'
        client = DjangoPidmanRestClient()
        self.assertEqual(client.baseurl['host'],
            'testpidman.library.emory.edu',
            'Client Base URL %s not expected value.' % client.baseurl)

        # credentials are stored for passing to request
        username, password = client._auth
        self.assertEqual('testuser', username,
            'Client username %s not the expected value' % username)
        self.assertEqual('testpass', password,
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

