#!/usr/bin/python

# Script to find and replace netloc of pids in a given domain.

import sys
import http.client as httplib
import json
import urllib2
from urlparse import parse_qs
import getopt
import urlparse
import re

from pidservices.clients import PidmanRestClient


def main():
  
  try:
      opts, args = getopt.getopt(sys.argv[1:], "hu:", ["--help", "--url1", "--url2"])
  except getopt.GetoptError, err:
      # print help information and exit:
      print str(err) 
      usage()
      sys.exit(2)

  # SCRIPT PARAMETERS
  global old_netloc  # script first parameter.
  global new_netloc  # script second parameter.
  global db_username      # pidmanager username to connect to the REST Pid Client
  global db_password      # pidmanager password  to connect to the REST Pid Client
  global db_baseurl       # pidmanager url to connect to the REST Pid Client (optional)
  #global domain = 'General purchased collections'
  global domain
  
  for o, a in opts:   
    usage()
    sys.exit()
      
  if (len(args)==5 or len(args)==6):
    print str(args)
  
    old_netloc = args[0]
    new_netloc = args[1]
    db_username = args[2]
    db_password = args[3]
    domain = args[4]
    if (len(args) == 6):
      db_baseurl = args[5]
    else: # use the test pid manager if not specified
      db_baseurl = 'https://testpid.library.emory.edu/'
       
  else:
    print '\nError: argument list incomplete. See usage example below.'
    usage()
    sys.exit()
  
        
  global client        
  client = PidmanRestClient(db_baseurl, db_username, db_password)
  
  current_page = 1
  count = 0
  max = 50000
    
  search_results = client.search_pids(type='purl', domain=domain, count=max)
  total_pages = search_results['page_count']
  
  page_results = search_results['results']
  print "\n=> Processing page[%d] that contains [%d] of a total of [%d] pages..." %(current_page, max, total_pages)
  
  count = process_page(current_page, page_results)

  current_page = current_page + 1  
  while (current_page <= total_pages):
    #search_results = client.search_pids(type='purl', domain='General purchased collections', page=current_page, count=max)
    search_results = client.search_pids(type='purl', domain=domain, page=current_page, count=max)
    page_results = search_results['results']
    print "\n=> Processing page[%d] of [%d] that contains [%d] pids." \
          %(current_page, total_pages, max)
    upd_count = process_page(current_page, page_results)
    count = count + upd_count    
    current_page = current_page + 1

  print "\n=> All done, total updated pids = [%d]." % count
  sys.exit()

def process_page(page, results):
  all_count = 0;
  updatedcount = 0

  for item in results:  
    targets = item['targets']
    for tg in targets:
      all_count = all_count + 1
      target_uri = tg['target_uri']
      scheme = str(urlparse.urlparse(target_uri).scheme)
      path = str(urlparse.urlparse(target_uri).path)
      params = str(urlparse.urlparse(target_uri).params)
      query = str(urlparse.urlparse(target_uri).query)
      fragment = str(urlparse.urlparse(target_uri).fragment)
      
      if target_uri.find(old_netloc) > 0:
        new_url = scheme + "://" + new_netloc
        if path:
          new_url += path
        if params:
          new_url += ";" + params 
        if query:
          new_url += "?" + query 
        if fragment:
          new_url += "#" + fragment
        
        client.update_purl_target(item['pid'], target_uri=new_url)
        updatedcount += 1

      
  print "   Page [%d] results: Updated[%d]." % (page, updatedcount)
  return updatedcount
  
def show_error(err):
  print err
  usage()
  sys.exit() 
      
def usage():
  bold = "\033[1m"
  bold_off = "\033[0;0m"
  msg = '\n'
  msg = msg + bold + 'Description:' + bold_off + ' Find and replace pid urls.\n'    
  msg = msg + bold + 'Usage:' + bold_off + ' migrate_pid_urls.py <old_base_domain> <new_base_domain> <pid username> <pid password> <domain> <pid manager url>.\n'
  msg = msg + bold + 'Example:' + bold_off + ' migrate_pid_urls.py "www.lexisnexis.com" "congressional.proquest.com" "username" "password" "General purchased collections" "https://testpid.library.emory.edu/"\n'    
  print msg
  sys.exit() 
    
if __name__ == "__main__":
    main()
    
    
