'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**

Module contains clases the build clients to interact with the Pidman Application
via services.

TODO: Test this note out to see what it gets us.

'''

import urllib, urllib2, httplib, base64, json
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
            raise urlib2.HTTPError(url, response.status, response.reason, None, None)
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
           raise urlib2.HTTPError(url, response.status, response.reason, None, None)
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


