'''
*"No question is so difficult to answer as that to which the answer is
obvious."* - **Karl Bismark**

Module contains clases the build clients to interact with the Pidman Application
via services.

TODO: Test this note out to see what it gets us.

'''

import urllib2, urllib, re

class PidmanRestClient(object):
    """
    Provides minimal REST client support for the pidmanager REST API.  See
    that project documentation for details on the REST API.  This class will
    build encapulated calls to the Pidman Rest API service.

    :param baseurl: base url of the api for the pidman REST service.
                    note this requires a trailing slash.
    :param username: optional username to query REST API with.
    :param password: optional password for username to query REST API

    """

    def __init__(self, baseurl, username="", password=""):
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
        passmgr.add_password(None, self.baseurl, self.username, self.password)
        handler = urllib2.HTTPBasicAuthHandler(passmgr)
        return urllib2.build_opener(handler)

    def request_pid(self, pid):
        pass

    def request_domain(self, domain):
        pass

    def search_pids(self, querydict={}):
        """
        Queries the PID search api and returns the data results.

        :param querydict: dict of attribute value pairs for PID searches.
                          Currently known valid values are:

                           * domain - exact domain uri for pid
                           * type - purl or ark
                           * pid - exact pid value
                           * target - exact target uri
                           * page - Page number of results to return
                           * count - Number of results to return on a single
                             page

        """

        querystring = urllib.urlencode(querydict) # Encode the params
        url = '%spids/' % self.baseurl # format the search url
        urllib2.install_opener(self.opener) # install the opener

        # Try our actual query and catch normal errors.
        try:
            return urllib2.urlopen(url, querystring).read()
        except urllib2.HTTPError as e:
            err = "%s for %s?%s" % (e, url, querystring)
            # print err
            return err
