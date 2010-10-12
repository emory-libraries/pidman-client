'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**
'''

import urllib2
import urllib

class PidmanRestClient:

    def __init__(self, baseurl, username="", password=""):
        """
        Provides minimal REST client support for the pidmanager REST API.  See
        that project documentation for details on the REST API.  This class will
        build encapulated calls to the Pidman Rest API service.

        :param baseurl: base url of the api for the pidman REST service.
                        note this requires a trailing slash.
        :param username: optional username to query REST API with.
        :param password: optional password for username to query REST API

        """
        self.baseurl = self._set_baseurl(baseurl)
        self.username = username
        self.password = password
        self.opener = self._get_opener()

    def _set_baseurl(self, baseurl):
        """
        Provides some cleanup for consistency on the input url.  If it has no
        trailing slash it adds one.

        :param baseurl: string of the base url for the rest api to be normalized

        """
        tail = re.compile('.*\/$')
        if tail.match(baseurl) is None: # Add forward slash to url if not there.
           baseurl = '/'.join([baseurl, ''])
        return baseurl

    def _get_opener(self):
        """
        Constructs the url opener for connection and authentication to the REST
        API service

        """
        passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passmgr.add_password(None, siteurl, self.username, self.password)
        handler = urllib2.HTTPBasicAuthHandler(passmgr)
        return urllib2.build_opener(handler)

    def request_pid(self, pid):
        pass

    def request_domain(self, domain):
        pass

    def search_pids(self, params={}):
        """
        Queries the PID search api and returns the data results.

        :param params: dict of attribute value pairs for PID searches.
                       Currently known valid values are:

                       * domain - exact domain uri for pid
                       * type - purl or ark
                       * pid - exact pid value
                       * target - exact target uri
                       * page - Page number of results to return
                       * count - Number of results to return on a single page

        """

        querystring = urllib.urlencode(params) # Encode the params
        url = '%spids/' % self.baseurl # format the search url
        urllib2.install_opener(self.opener) # install the opener

        return urllib2.urlopen(url, querystring).read()
