'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**

Module contains classes that build clients to interact with the Pidman Application
via services.
'''

import json
import logging
import re
import urllib
from urllib.parse import urlparse
import requests

from pidservices import __version__

logger = logging.getLogger(__name__)

# characters expected to be present in NOID portion of ARKs and PURLs (noid template .zek)
NOID_CHARACTERS = '0123456789bcdfghjkmnpqrstvwxz'
ARK_REGEXP = re.compile('^(?P<nma>https?://[a-z./]+/)?ark:/(?P<naan>[0-9]+)/(?P<noid>[%s]+)(?:/(?P<qualifier>.*))?$' % \
    NOID_CHARACTERS, re.IGNORECASE)

def is_ark(str):
    '''Check if a string matches a regular expression for an ARK, in either
    resolvable url form or short-form id, with or without qualifiers.

    :param str: string to check
    :returns: :class:`re.MatchObject` or None (can be treated as a boolean)
    '''
    return ARK_REGEXP.match(str)

def parse_ark(ark):
    '''Parse an ARK into its component parts.  Uses the same regular expression
    as :meth:`~pidservices.clients.is_ark`; matches both short and resolvable
    ARKs, with and without qualifiers.

    :param ark: ARK string to parse
    :returns: dictionary with parsed ARK information or None if the regular
        expression does not match.  Dictionary keys in the return:

        - **nma** - Name Mapping Authority (base url portion of resolvable ark)
        - **naan** - Name Assigning Authority Number
        - **noid** - Nice Opaque Identifier
        - **qualifier** - qualifier
    '''
    matches = is_ark(ark)
    if matches is not None:
        return matches.groupdict()


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
    _auth = None
    # Requests verifies SSL certificates for HTTPS requests, just like a web browser.
    # By default, SSL verification is enabled, and Requests will throw a SSLError if
    # it's unable to verify the certificate.
    headers = {
        'User-Agent': 'PidmanRestClient/%s (python-requests/%s)' % \
            (__version__, requests.__version__)
    }

    pid_types = ['ark', 'purl']
    # pattern for generating a REST api url for pid create/access/update
    # - no trailing slash here (used to distinguish unqualified target)
    _rest_pid_uri = '%(base_url)s/%(type)s/%(noid)s'
    # pattern for generating REST api url for target access/update/delete
    _rest_target_uri = '%(base_url)s/%(type)s/%(noid)s/%(qualifier)s'

    # This token is used when creating arks for targets.
    # The portion of the url that contains this token should be replaced with a noid
    pid_token = '{%PID%}'

    def __init__(self, url, username="", password=""):
        self._set_baseurl(url)

        # create a requests session to be used for all API calls
        self.session = requests.Session()
        # Set headers that should be passed with every request

        # Requests verifies SSL certificates for HTTPS requests, just like a web browser.
        # By default, SSL verification is enabled, and Requests will throw a SSLError if
        # it's unable to verify the certificate.
        self.session.headers = {
            'User-Agent': 'pidmanclient/%s (python-requests/%s)' % \
                (__version__, requests.__version__)
        }
        # store auth if credentials were specified
        if username and password:
            self._auth = (username, password)

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

    def absolute_url(self, path):
        """
        Prep an API URL for access based on base url.
        """
        url_info = self.baseurl.copy()
        url_info['local_path'] = path.lstrip('/')
        return '%(scheme)s://%(host)s%(path)s/%(local_path)s' % url_info

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

    def _make_request(self, reqmeth, url, params=None, body=None,
        expected_response=requests.codes.ok, accept="application/json"):
        '''Make an API request.  Common functionality for making http requests
        and simple error handling.  Defaults are set so that simple access
        requests can specify very few parameters.

        Checks the returned response status code against the expected response,
        and raises an :class:`urllib2.HTTPError` if they are not equal.  Otherwise,
        the response object is returned for any further processing.

        :param url: url to request
        :param body: data to send in request body, if any (optional)
        :param params: dictionary of query string or post parameters, if any
        :param expected_response: expected http status code on the returned
            response; if the response does not match, an error is raised - can be
            either a single status code, or a list of valid codes; defaults to 200
        :param accept: expected/accepted content type in the response; defaults
            to application/json

        :returns: the content of the response, based on the specified accept
            format: if accept is ``application/json``, loads the response as JSON
            and returns the resulting object; if accept is ``text/plain``, returns
            the body of the response.  Otherwise, returns the
            :class:`request.Response` response object.
        '''
        method_name = reqmeth.__name__.upper()
        request_options = {}
        if body is not None:
            request_options['data'] = body
        if params is not None:
            request_options['params'] = params
        headers = {}
        # any api calls that modify data require authentication
        if method_name in ['PUT', 'POST', 'DELETE']:
            # only include auth information when required
            request_options['auth'] = self._auth

        # set headers that vary depending on the request
        # All headers must be strings.

        # - set content length based on the actual body
        headers["Content-Length"] = str(len(body)) if body is not None else '0'
        # - set content type based on the data being sent (if any)
        # for current implementation, we can make the following assumptions:
        # - all POST methods are currently form-encoded key=>value data

        if method_name == 'POST':
            headers["Content-type"] = "application/x-www-form-urlencoded"
        # - all PUT methods currently use JSON-encoded data in request body
        elif method_name == 'PUT':
            headers["Content-type"] = "application/json"
        # - expect no body for GET and DELETE requests, so no content-type

        # - expected result format
        headers['Accept'] = accept

        # absolutize url based on configured pidman base url
        url = self.absolute_url(url)
        logger.debug('Request: %s %s %s <![BODY[%s]]>', method_name, url, headers, body)
        response = reqmeth(url, headers=headers, **request_options)
        # convert expected response code into list for simpler comparison
        if not isinstance(expected_response, list):
            expected_response = [expected_response]

        if response.status_code not in expected_response:
            # Some errors (e.g., bad request) include a more detailed error
            # message in response body - if present, add to error message detail
            text = response.content
            if text is not None and len(text):
                detail = '%s: %s' % (response.status_code, text)
                raise requests.exceptions.HTTPError(detail, response=response)
            else:
                # otherwise let requests raise the error
                response.raise_for_status()

        if accept == 'application/json':
            return response.json()
        elif accept == 'text/plain':
            return response.content
        else:
            return response

    def get(self, *args, **kwargs):
        return self._make_request(self.session.get, *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._make_request(self.session.put, *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._make_request(self.session.post, *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._make_request(self.session.delete, *args, **kwargs)

    domain_url = '/domains/'

    def list_domains(self):
        """
        Returns the default domain list from the rest server.
        """
        return self.get(self.domain_url)

    def create_domain(self, name, policy=None, parent=None):
        """
        Creates a POST request to the rest api with attributes to create
        a new domain.

        :param name: label or title for the new Domain (unicode)
        :param policy: policy title
        :param parent: parent uri

        """
        # Do some error checking before we bother sending the request.
        if not name or name == '':
            raise Exception('Name value cannot be None or empty!')

        # build the request.
        domain_info = {'name': name}
        # parent & policy are optional; only include in the request if specified
        if policy is not None:
            domain_info['policy'] = policy
        if parent is not None:
            domain_info['parent'] =  parent

        # returns the URI for the newly-created domain on success
        return self.post(self.domain_url, body=domain_info, expected_response=requests.codes.created,
                         accept='text/plain')

    def get_domain(self, domain_id):
        """
        Requests a domain by id.

        :param domain_id: ID of the domain to return.

        """
        url = '%s%s/' % (self.domain_url, urllib.quote(str(domain_id)))
        return self.get(url)

    def update_domain(self, domain_id, name=None, policy=None, parent=None):
        """
        Updates an existing domain with new information.

        :param domain_id: ID of the domain to update
        :param name: label or title for the domain
        :param policy: policy title
        :param parent: parent uri

        """
        domain_info = {}
        if name is not None:
            domain_info['name'] = name
        if policy is not None:
            domain_info['policy'] = policy
        if parent is not None:
            domain_info['parent'] = parent

        # Setup the data to pass in the request.
        url = '%s%s/' % (self.domain_url, urllib.quote(str(domain_id)))
        body = json.dumps(domain_info)

        if not domain_info:
            raise Exception("No domain update data specified")

        # If successful the view returns the object just updated.
        return self.put(url, body=body)

    def search_pids(self, pid=None, type=None, target=None, domain=None,
            domain_uri=None, page=None, count=None):
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
        # generate a dictionary with any parameters that are set
        query = dict([(key, val) for key, val in locals().iteritems() if
                      key not in ['self'] and val])

        url = 'pids/'
        return self.get(url, params=query)

    def create_pid(self, type, domain, target_uri, name=None, external_system=None,
                external_system_key=None, policy=None, proxy=None,
                qualifier=None):
        """
        POST a request to the REST api with the specified values to create a new
        pid with a single target.

        :param type: type of pid to create (purl or ark)
        :param domain: Domain new pid should belong to (specify by REST resource URI)
        :param target_uri: URI the pid target should resolve to
        :param name: name or identifier for the pid (unicode)
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

        # on success, returns new purl or ark in resolvable form as plain text
        return self.post(url, body=pid_opts, expected_response=requests.codes.created,
                         accept='text/plain')

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
        return self.get(url)

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
        return self.get(url)

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
            raise Exception("No update data specified")

        # Setup the data to pass in the request.
        data = json.dumps(pid_info)
        # If successful the view returns the object just updated.
        return self.put(url, body=data)

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

        # for ARK, either 200 or 201 is valid (could actually create a new qualifier here)
        success_codes = [requests.codes.ok]
        if type == 'ark':
            success_codes.append(requests.codes.created)

        # Setup the data to pass in the request.
        data = json.dumps(target_info)
        return self.put(url, body=data, expected_response=success_codes)

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
        pid_type = 'ark'
        # generate target url and check pid type
        url = self._target_url(pid_type, noid, qualifier)
        self.delete(url, accept='text/plain')
        # no processing to do with the response - if status code was 200, success
        return True
