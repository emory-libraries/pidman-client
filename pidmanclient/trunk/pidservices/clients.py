'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**

Module contains classes that build clients to interact with the Pidman Application
via services.

TODO: Test this note out to see what it gets us.

'''

import base64
import httplib
import json
import urllib
import urllib2
from urlparse import urlparse

class PidmanRestClient(object):
    """
    Provides minimal REST client support for the pidmanager REST API.  See
    that project documentation for details on the REST API.  This class will
    build encapsulated calls to the Pidman Rest API service.

    API calls that create, delete, or modify objects require valid credentials
    for a user with appropriate permissions.  API calls are made using Basic
    Authorization, which base64 encodes username and password.  It is recommended
    to use HTTPS for any REST API calls that require credentials.

    :param baseurl: base url of the api for the pidman REST service., e.g.
                    ``http://my.domain.com/pidserver``
    :param username: optional username for REST API access
    :param password: optional password 

    """
    baseurl = {
        'scheme': None,
        'host': None,
        'path': None,
    }

    headers = {        
        "User-Agent": "PidmanRestClient",       # TODO: can we include module version here?
    }

    pid_types = ['ark', 'purl']
    # pattern for generating a REST api url for pid create/access/update
    # - no trailing slash here (used to distinguish unqualified target)
    _rest_pid_uri = '%(base_url)s/%(type)s/%(noid)s'
    # pattern for generating REST api url for target access/update/delete
    _rest_target_uri = '%(base_url)s/%(type)s/%(noid)s/%(qualifier)s'

    def __init__(self, url, username="", password=""):
        self._set_baseurl(url)        
        self._set_auth_token(username, password)
        # FIXME: should we generate an auth token when username & password are not
        # specified? Credentials are required for create/delete/update methods...
        # Seems weird to build an auth token for blank username, blank password
        self.connection = self._get_connection()

    def _set_baseurl(self, url):
        """
        Provides some cleanup for consistency on the input url.  If it has no
        trailing slash it adds one.

        :param baseurl: string of the base url for the rest api to be normalized

        """
        obj = urlparse(url.rstrip('/'))
        self.baseurl['scheme'] = obj.scheme
        self.baseurl['host'] = obj.netloc
        self.baseurl['path'] = obj.path

    def _get_baseurl(self):
        """
        Returns the baseurl used.  Mostly for error checking.
        """
        return '%s://%s%s' % (self.baseurl['scheme'], self.baseurl['host'], self.baseurl['path'])

    def _get_connection(self):
        """
        Constructs the proper httplib connection object based on the
        baseurl.scheme value.

        """
        if self.baseurl['scheme'] is 'https':
            return httplib.HTTPSConnection(self.baseurl['host'])
        return httplib.HTTPConnection(self.baseurl['host'])
    
    def _secure_headers(self):
        """Returns a copy of headers with the intent of using that as a
        method variable so I'm not passing username and password by default.
        It's private because... get your own darn secure heaeders ya hippie!
        """
        headers = self.headers.copy()
        headers['AUTHORIZATION'] = self._auth_token
        return headers

    def _set_auth_token(self, username, password):
        """Generate and store Basic authorization token for use with API calls
        that require user credentials."""
        token = base64.b64encode('%s:%s' % (username, password))
        self._auth_token = 'Basic %s' % token

    def _check_pid_type(self, type):
        '''Several pid- and target-specific methods take a pid type, but only
        two values are allowed.  Throw an exception if we got anything else.'''
        if type not in self.pid_types:
            raise Exception("Pid type '%s' is not recognized" % type)

    def _pid_url(self, type, noid=''):
        '''Generate REST pid url.  Runs :meth:`_check_pid_type` to check
        that type is valid before generating url.

        :param type: type of pid (ark or purl)
        :param noid: pid identifier, or empty for create ark/purl rest uri
        '''
        self._check_pid_type(type)
        return self._rest_pid_uri % {
            'base_url': self.baseurl['path'],
            'type': type,
            'noid': noid,
        }

    def _target_url(self, type, noid, qualifier=''):
        '''Generate REST target url.  Runs :meth:`_check_pid_type` to check
        that type is valid before generating url.

        :param type: type of pid (ark or purl)
        :param noid: pid identifier, or empty for create ark/purl rest uri
        :param qualifier: target qualifier, defaults to unqualified target
        '''
        self._check_pid_type(type)
        return self._rest_target_uri % {
            'base_url': self.baseurl['path'],
            'type': type,
            'noid': noid,
            'qualifier': qualifier,
        }

    def _make_request(self, url, method='GET', body=None, expected_response=200,
        requires_auth=False, accept="application/json"):
        ''' Make an API request.  Common functionality for making http requests
        and simple error handling.  Defaults are set so that simple access
        requests can specify very few parameters.

        Checks the returned response status code against the expected response,
        and raises an :class:`urllib2.HTTPError` if they are not equal.  Otherwise,
        the response object is returned for any further processing.

        :param url: url to request
        :param method: http method to use when making the request; default is GET
        :param body: data to send in request body, if any (optional)
        :param expected_response: expected http status code on the returned
            response; if the response does not match, an error is raised
        :param requires_auth: boolean, defaults to False; when True, authorization
            headers will be included in the request
        :param accept: expected/accepted content type in the response; defaults
            to application/json

        :returns: the content of the response, based on the specified accept
            format: if accept is ``application/json``, loads the response as JSON
            and returns the resulting object; if accept is ``text/plain``, returns
            the body of the response.  Otherwise, returns the
            :class:`httplib.HTTPResponse` response object.
        '''
        if requires_auth:
            # only include auth header when required
            headers = self._secure_headers()
        else:
            headers = self.headers

        # set headers that vary depending on the request

        # set content length based on the actual body
        headers["Content-Length"] = len(body) if body is not None else 0

        # set content type based on the data being sent (if any)
        # for current implementation, we can make the following assumptions:
        # - all POST methods are currently form-encoded key=>value data
        headers["Content-type"] = "application/x-www-form-urlencoded"
        # - all PUT methods currently use JSON-encoded data in request body
        headers["Content-type"] = "application/json"
        # - expect no body for GET and DELETE requests, so no content-type

        # expected result format
        headers['Accept'] = accept
        
        self.connection.request(method, url, body, headers)
        response = self.connection.getresponse()

        if response.status is not expected_response:
            # Some errors (e.g., bad request) include a more detailed error
            # message in response body - if present, add to error message detail
            text = response.read()
            if text is not None and len(text):
                detail = '%s: %s' % (response.reason, text)
            else:
                detail = response.reason
            
            raise urllib2.HTTPError(url, response.status, detail, None, None)

        if accept == 'application/json':
            return json.loads(response.read())
        elif accept == 'text/plain':
            return response.read()
        else:
            return response

    def list_domains(self):
        """
        Returns the default domain list from the rest server.
        """        
        url = '%s/domains/' % self.baseurl['path']
        return self._make_request(url)
        
    def create_domain(self, name, policy=None, parent=None):
        """
        Creates a POST request to the rest api with attributes to create
        a new domain.

        :param name: label or title for the new  Domain
        :param policy: policy title
        :param parent: parent uri
        
        """
        # Do some error checking before we bother sending the request.
        if not name or name == '':
            raise Exception('Name value cannot be None or empty!')

        # build the request.
        domain = {'name': name, 'policy': policy, 'parent': parent}
        params = urllib.urlencode(domain)
        url = '%s/domains/' % self.baseurl['path']
        # returns a plain text response about success.
        return self._make_request(url, 'POST', params, expected_response=201,
                            requires_auth=True, accept='text/plain')

    def request_domain(self, domain_id):
        """
        Requests a domain by id.

        :param domain_id: ID of the domain to return.
        
        """
        url = '%s/domains/%s/' % (self.baseurl['path'], urllib.quote(str(domain_id)))
        return self._make_request(url)

    def update_domain(self, id, name=None, policy=None, parent=None):
        """
        Updates an existing domain with new information.

        :param name: label or title for the Domain
        :param policy: policy title
        :param parent: parent uri
        
        """
        # Work a bit with the arguments to get them in a dict and filtered.
        domain = {}
        args = locals()
        del args['self']
        del args['id']
        for key, value in args.items():
            if value:
                domain[key] = value
        
        # Setup the data to pass in the request.
        url = '%s/domain/%s/' % (self.baseurl['path'], id)
        body = '%s' % json.dumps(domain)

        if not domain:
            raise urllib2.HTTPError(url, 412, "No data provided for a valid updated", body, None)

        # If successful the view returns the object just updated.
        return self._make_request(url, 'PUT', body, requires_auth=True)

    def delete_domain(self, domain):
        """
        You can't delete domains, don't even try.

        :param domain: Any value of a domain, it doesn't matter.  I wont let you
                       delete it anyway.
        """
        raise Exception("WHAT YOU TALKIN' 'BOUT WILLIS!?!?!  You can't delete domains.")

    def search_pids(self, pid=None, type=None, target=None, domain=None, domain_uri=None, page=None, count=None):
        """
        Queries the PID search api and returns the data results.

        :param domain: Exact domain name for pid
        :param domain_uri: URI of a domain.
        :param type: purl or ark
        :param pid: Exact pid value
        :param target: Exact target uri
        :param page: Page number of results to return
        :param count: Number of results to return on a single page.

        """
        # If any of the arguments have been set, construct a querystring out of
        # them.  Skip anything left null.
        query = {}
        args = locals()
        del args['self']
        for key, value in args.items():
            if value:
                query[key] = value

        querystring = urllib.urlencode(query)
        url = '%s/pids/?%s' % (self.baseurl['path'], querystring)
        return self._make_request(url)

    def create_pid(self, type, domain, target_uri, name=None, external_system=None,
                external_system_key=None, policy=None, proxy=None,
                qualifier=None):
        """
        POST a request to the REST api with the specified values to create a new
        pid with a single target.

        :param type: type of pid to create (purl or ark)
        :param domain: Domain new pid should belong to (specify by REST resource URI)
        :param target_uri: URI the pid target should resolve to
        :param name: name or identifier for the pid
        :param external_system: external system name
        :param external_system_id: pid identifier in specified external system
        :param policy: policy title
        :param proxy: proxy name
        :param qualifier: (ARK only) create a qualified target
        :returns: newly created ARK or PURL in resolvable form
        :rtype: string
        """
        # rest url url for creating the new pid
        url = self._pid_url(type)       # also checks pid type

        # build the request parameters
        pid_opts = {'domain': domain, 'target_uri': target_uri}
        if name is not None:
            pid_opts['name'] = name
        if external_system is not None:
            pid_opts['external_system_id'] = external_system
        if external_system_key is not None:
            pid_opts['external_system_key'] = external_system_key
        if policy is not None:
            pid_opts['policy'] = policy
        if proxy is not None:
            pid_opts['proxy'] = proxy
        if qualifier is not None:
            pid_opts['qualifier'] = qualifier

        data = urllib.urlencode(pid_opts)
        # on success, returns new purl or ark in resolvable form as plain text
        return self._make_request(url, 'POST', data, expected_response=201,
                            requires_auth=True, accept='text/plain')

    def create_purl(self, *args, **kwargs):
         '''Convenience method to create a new PURL.  See :meth:`create_pid` for
         details and supported parameters.'''
         return self.create_pid('purl', *args, **kwargs)

    def create_ark(self, *args, **kwargs):
         '''Convenience method to create a new ARK.  See :meth:`create_pid` for
         details and supported parameters.'''
         return self.create_pid('ark', *args, **kwargs)

    def get_pid(self, type, noid):
        """Get information about a single pid, identified by type and noid.

        :param type: type of pid (ark or purl)
        :param noid: noid identifier for the requested pid
        :returns: a dictionary of information about the requested pid
        """
        # rest url for accessing the requested pid
        url = self._pid_url(type, noid)       # also checks pid type
        return self._make_request(url)

    def get_purl(self, noid):
         '''Convenience method to access information about a purl.  See
         :meth:`get_pid` for more details.'''
         return self.get_pid('purl', noid)

    def get_ark(self, noid):
         '''Convenience method to access information about an ark.  See
         :meth:`get_pid` for more details.'''
         return self.get_pid('ark', noid)

    def get_target(self, type, noid, qualifier=''):
        '''Get information about a single purl or ark target, identified by pid
        type, noid, and qualifier.

        :param type: type of pid (ark or purl)
        :param noid: noid identifier for the pid the target belongs to
        :param qualifier: target qualifier - defaults to unqualified target
        :returns: a dictionary of information about the requested target
        '''
        # generate target url and check pid type
        url = self._target_url(type, noid, qualifier)
        return self._make_request(url)

    def get_purl_target(self, noid):
        'Convenience method to retrieve information about a purl target.'
        # probably redundant, since a purl only has one target, but including for consistency
        return self.get_target('purl', noid)    # purl can *only* use default qualifier

    def get_ark_target(self, noid, qualifier):
        'Convenience method to retrieve information about an ark target.'
        return self.get_target('ark', noid, qualifier)

    def update_pid(self, type, noid, domain=None, name=None, external_system=None,
                external_system_key=None, policy=None):
        '''Update an existing pid with new information.
        
        :param type: type of pid (purl or ark)
        :param domain: Domain pid should belong to (specify by REST resource URI)        
        :param name: name or identifier for the pid
        :param external_system: external system name
        :param external_system_id: pid identifier in specified external system
        :param policy: policy title
        :returns: a dictionary of information for the update pid
        '''
        # rest url url for updating the requested pid
        url = self._pid_url(type, noid)       # also checks pid type

        pid_info = {}
        # only include fields that are specified - otherwise, will blank out value
        # on the pid (e.g., remove a policy or external system)
        if domain is not None:
            pid_info['domain'] = domain
        if name is not None:
            pid_info['name'] = name
        if external_system is not None:
            pid_info['external_system_id'] = external_system
        if external_system_key is not None:
            pid_info['external_system_key'] = external_system_key
        if policy is not None:
            pid_info['policy'] = policy

        # all fields are optional, but at least *one* should be provided
        if not pid_info:
            raise Exception("No update data specified!")

        # Setup the data to pass in the request.
        data = json.dumps(pid_info)
        # If successful the view returns the object just updated.
        return self._make_request(url, 'PUT', data, requires_auth=True)

    def update_purl(self, *args, **kwargs):
         '''Convenience method to update an existing purl.  See :meth:`update_pid`
         for details and supported parameters.'''
         return self.update_pid('purl', *args, **kwargs)

    def update_ark(self, *args, **kwargs):
         '''Convenience method to update an existing ark.  See :meth:`update_pid`
         for details and supported parameters.'''
         return self.update_pid('ark', *args, **kwargs)

    def update_target(self, type, noid, qualifier='', target_uri=None, proxy=None,
                      active=None):
        '''Update a single pid target.

        This method can be used to add new targets to an existing ARK.

        :param type: type of pid the target belongs to (purl or ark)
        :param noid: noid identifier for the pid the target belongs to
        :param qualifier: target qualifier; defaults to unqualified target
        :param target_uri: URI the target should resolve to
        :param proxy: name of the proxy that should be used to resolve the target
        :param active: boolean, indicating whether the target should be considered
            active (inactive targets will not be resolved)
        :returns: dictionary of information about the updated target.
        '''
        # generate target url and check pid type
        url = self._target_url(type, noid, qualifier)

        target_info = {}
        # only include fields that are specified - otherwise, will blank out value
        # on the target (e.g., remove a proxy)
        if target_uri is not None:
            target_info['target_uri'] = target_uri
        if proxy is not None:
            target_info['proxy'] = proxy
        if active is not None:
            target_info['active'] = active

        # all fields are optional, but at least *one* should be provided
        if not target_info:
            raise Exception("No update data specified!")

        # Setup the data to pass in the request.
        data = json.dumps(target_info)
        return self._make_request(url, 'PUT', data, requires_auth=True)


    def update_purl_target(self, noid, *args, **kwargs):
         '''Convenience method to update a single existing purl target.  See
         :meth:`update_target` for details and supported parameters.  Qualifier
         parameter should **not** be provided when using this method since
         a PURL may only have one, unqualified target.'''
         return self.update_target('purl', noid, '', *args, **kwargs)

    def update_ark_target(self, *args, **kwargs):
         '''Convenience method to update a single existing ark target.  See
         :meth:`update_target` for details and supported parameters.'''
         return self.update_target('ark', *args, **kwargs)

    def delete_ark_target(self, noid, qualifier=''):
        '''Delete an ARK target.  (Delete is not supported for PURL targets.)

        :param noid: noid identifier for the pid the target belongs to
        :param qualifier: target qualifier; defaults to unqualified target
        :returns: True on successful deletion
        '''
        type = 'ark'
        # generate target url and check pid type
        url = self._target_url(type, noid, qualifier)
        self._make_request(url, 'DELETE', requires_auth=True, accept='text/plain')
        # no processing to do with the response - if status code was 200, success
        return True
