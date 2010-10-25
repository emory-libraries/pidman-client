'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**

Module contains clases the build clients to interact with the Pidman Application
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
    build encapulated calls to the Pidman Rest API service.

    :param baseurl: base url of the api for the pidman REST service.
                    note this requires **NO** trailing slash. example
                    'http://my.domain.com/pidserver'
    :param username: optional username to query REST API with.
    :param password: optional password for username to query REST API.  Stored
                     with base64 encoding.

    """
    baseurl = {
        'scheme': None,
        'host': None,
        'path': None,
    }

    headers = {
        "Content-type": "application/rest-urlencoded",
        "Accept": "text/plain",
        "Content-Length": "0",
        "User-Agent": "x-www-form-urlencoded format",
    }

    pid_types = ['ark', 'purl']

    def __init__(self, url, username="", password=""):
        self._set_baseurl(url)
        self.username = username
        self._set_password(password)
        self.connection = self._get_connection()

    def _set_baseurl(self, url):
        """
        Provides some cleanup for consistency on the input url.  If it has no
        trailing slash it adds one.

        :param baseurl: string of the base url for the rest api to be normalized

        """
        obj = urlparse(url)
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
        headers["username"] = self.username
        headers["password"] = self.password
        return headers

    def _set_password(self, password):
        """Base 64 encodes the password."""
        self.password = base64.b64encode(password)

    def _check_pid_type(self, type):
        '''Several pid- and target-specific methods take a pid type, but only
        two values are allowed.'''
        if type not in self.pid_types:
            raise Exception('Pid type is not recognized')

    def list_domains(self):
        """
        Returns the default domain list from the rest server.
        """
        headers = self.headers
        conn = self.connection
        url = '%s/domains/' % self.baseurl['path']
        conn.request("GET", url, None, headers)
        response = conn.getresponse()
        if response.status is not 200:
            conn.close()
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            data = response.read()
            conn.close()
            return json.loads(data)
        
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

        headers = self._secure_headers()

        # Work the request.
        domain = {'name': name, 'policy': policy, 'parent': parent}
        params = urllib.urlencode(domain)
        conn = self.connection
        url = '%s/domains/' % self.baseurl['path']
        conn.request("POST", url, params, headers)
        response = conn.getresponse()
        if response.status is not 201: # 201 is the expected return on create.
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            return response.read() # Should be a text response about success.

    def request_domain(self, domain_id):
        """
        Requests a domain by id.

        :param domain_id: ID of the domain to return.
        
        """
        headers = self._secure_headers()
        conn = self.connection
        url = '%s/domains/%s/' % (self.baseurl['path'], urllib.quote(str(domain_id)))
        conn.request("GET", url, None, headers)
        response = conn.getresponse()
        if response.status is not 200:
           raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            data = response.read() 
            return json.loads(data)

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
        headers = self._secure_headers()
        url = '%s/domain/%s/' % (self.baseurl['path'], id)
        body = '%s' % json.dumps(domain)

        if not domain:
            raise urllib2.HTTPError(url, 412, "No data provided for a valid updated", body, None)

        conn = self.connection
        conn.request("PUT", url, body, headers)
        response = conn.getresponse()
        if response.status is not 200:
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            # If successful the view returns the object just updated.
            data = response.read()
            return json.loads(data)

    def delete_domain(self, domain):
        """
        You can't delete domains, don't even try.

        :param domain: Any value of a domain, it doesn't matter.  I wont let you
                       delete it anyway.
        """
        raise Exception("WHAT YOU TALKIN' 'BOUT WILLIS!?!?!  You can't delete domains.")

    def search_pids(self, pid=None, type=None, target=None, domain=None, page=None, count=None):
        """
        Queries the PID search api and returns the data results.

        :param domain: Exact domain uri for pid
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
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain", "Content-Length": "0"}
        conn = self.connection
        url = '%s/pids/?%s' % (self.baseurl['path'], querystring)
        conn.request('GET', url, None, headers)
        response = conn.getresponse()
        if response.status is not 200:
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            data = response.read()
            return data

    def create_pid(self, type, domain, target_uri, name=None, external_system=None,
                external_system_key=None, policy=None, proxy=None,
                qualifier=None):
        """
        Creates a POST request to the rest api with attributes to create
        a new pid.

        :param type: type of pid to create (purl or ark)
        :param domain: Domain new pid should belong to (specify by REST resource URI)
        :param target_uri: URI the pid target should resolve to
        :param name: name or identifier for the pid
        :param external_system: external system name
        :param external_system_id: pid identifier in specified external system
        :param policy: policy title
        :param proxy: proxy name
        :param qualifier: ARK only - create a qualified target

        """
        self._check_pid_type(type)

        headers = self._secure_headers()

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

        params = urllib.urlencode(pid_opts)
        conn = self.connection
        url = '%s/%s/' % (self.baseurl['path'], type)
        conn.request("POST", url, params, headers)
        response = conn.getresponse()
        if response.status is not 201: # 201 is the expected return on create.
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            return response.read() # Should be new purl or ark (resolvable form)

    def create_purl(self, *args, **kwargs):
         '''Convenience method to create a new purl.  See :meth:`create_pid` for
         details and supported parameters.'''
         return self.create_pid('purl', *args, **kwargs)

    def create_ark(self, *args, **kwargs):
         '''Convenience method to create a new ark.  See :meth:`create_pid` for
         details and supported parameters.'''
         return self.create_pid('ark', *args, **kwargs)

    def get_pid(self, type, noid):
        """Get information about a single pid, identified by type and noid.

        :param type: type of pid (ark or purl)
        :param noid: noid identifier for the requested pid
        :returns: a dictionary of information about the requested pid
        """
        self._check_pid_type(type)
        
        headers = self._secure_headers()
        conn = self.connection
        # *without* trailing slash for pid info; use trailing slash for unqualified target 
        url = '%s/%s/%s' % (self.baseurl['path'], type, noid)
        conn.request("GET", url, None, headers)     # None = no data in body of request
        response = conn.getresponse()
        if response.status is not 200:
           raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            data = response.read()
            return json.loads(data)

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
        self._check_pid_type(type)
        
        headers = self._secure_headers()
        conn = self.connection
        url = '%s/%s/%s/%s' % (self.baseurl['path'], type, noid, qualifier)
        conn.request("GET", url, None, headers)     # None = no data in body of request
        response = conn.getresponse()
        if response.status is not 200:
           raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            data = response.read()
            return json.loads(data)

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
        
        '''
        self._check_pid_type(type)

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
        headers = self._secure_headers()
        url = '%s/%s/%s' % (self.baseurl['path'], type, noid)
        body = json.dumps(pid_info)

        conn = self.connection
        conn.request("PUT", url, body, headers)
        response = conn.getresponse()
        if response.status is not 200:
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            # If successful the view returns the object just updated.
            data = response.read()
            return json.loads(data)

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
        '''Update a single pid target.  This method can be used to create new
        qualified targets on an existing ARK pid.

        :param type: type of pid the target belongs to (purl or ark)
        :param noid: noid identifier for the pid the target belongs to
        :param qualifier: target qualifier; defaults to unqualified target
        :param target_uri: URI the target should resolve to
        :param proxy: name of the proxy that should be used to resolve the target
        :param active: boolean, indicating whether the target should be considered
            active (inactive targets will not be resolved)
        :returns: dictionary of information about the updated target.
        '''
        self._check_pid_type(type)

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
        headers = self._secure_headers()
        url = '%s/%s/%s/%s' % (self.baseurl['path'], type, noid, qualifier)
        body = json.dumps(target_info)
        conn = self.connection
        conn.request("PUT", url, body, headers)
        response = conn.getresponse()
        if response.status is not 200:
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            # If successful the view returns the object just updated.
            data = response.read()
            return json.loads(data)


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
        '''Delete an ARK target.  (Not supported for PURL targets.)

        :param noid: noid identifier for the pid the target belongs to
        :param qualifier: target qualifier; defaults to unqualified target
        :returns: True on successful deletion
        '''
        type = 'ark'
        headers = self._secure_headers()
        url = '%s/%s/%s/%s' % (self.baseurl['path'], type, noid, qualifier)
        conn = self.connection
        conn.request("DELETE", url, None, headers)  # no body request
        response = conn.getresponse()
        if response.status is not 200:
            raise urllib2.HTTPError(url, response.status, response.reason, None, None)
        else:
            return True
