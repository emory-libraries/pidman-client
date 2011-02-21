#!/usr/bin/python

# LSDI script to update all fedora-based ARK target for LDSI content
# This script is part of the fedora 3.4 migration.
# This script is a ONE-TIME script, and uses the pid client service.
# The format of the ARK string will be updated from the now-deprecated 
# API-A-Lite and switch over to the REST API url format.
# Documentation on the fedora REST API can be found at:
#   https://wiki.duraspace.org/display/FCR30/REST+API
#   for datastreams see link (getObjectProfile)
#   for top level object see link (getDatastreamDissemination)

import sys
import httplib
import json
import urllib2
from urlparse import parse_qs
import getopt
import urlparse
import re

from pidservices.clients import PidmanRestClient, is_ark, parse_ark

def main():
  
  try:
      opts, args = getopt.getopt(sys.argv[1:], "hf:", ["--help", "--url", "--port"])
  except getopt.GetoptError, err:
      # print help information and exit:
      print str(err) 
      usage()
      sys.exit(2)

  # SCRIPT PARAMETERS
  global old_fedora_base  # script first parameter.
  global new_fedora_base  # script second parameter.
  global db_username      # pidmanager username to connect to the REST Pid Client
  global db_password      # pidmanager password  to connect to the REST Pid Client
  global db_baseurl       # pidmanager url to connect to the REST Pid Client (optional)
  
  for o, a in opts:   
    usage()
    sys.exit()
      
  if (len(args)==4 or len(args)==5):
    old_fedora_base = args[0]
    new_fedora_base = args[1]
    db_username = args[2]
    db_password = args[3] 
    if (len(args) == 5):
      db_baseurl = args[4]
    else: # use the test pid manager if not specified
      db_baseurl = 'https://testpid.library.emory.edu/'
      
    # validate that each arg starts with http and ends with a port number
    validate(old_fedora_base, new_fedora_base)     
  else:
    print '\nError: argument list incomplete. See usage example below.'
    usage()
    sys.exit()
  
        
  global client        
  client = PidmanRestClient(db_baseurl, db_username, db_password)
  connection = client._get_connection()
  
  current_page = 1
  count = 0
  max = 500
    
  # search for existing arks by domain where type='ark', domain='LSDI'
  search_results = client.search_pids(type='ark', domain='LSDI', count=max)
  total_pages = search_results['page_count']
  page_link_1 = search_results['first_page_link']
  page_link = page_link_1[0:-1]
  
  print "\n=> Processing page[%d] that contains [%d] of a total of [%d] pages ..." %(current_page, max, total_pages)
  page_results = search_results['results']
  count = process_page(current_page, page_results)
  current_page = current_page + 1  
  while (current_page <= total_pages):
    search_results = client.search_pids(type='ark', domain='LSDI', page=current_page, count=max)
    page_results = search_results['results']    
    print "\n=> Processing page[%d] of [%d] that contains [%d] arks." \
          %(current_page, total_pages, max)
    upd_count = process_page(current_page, page_results)
    count = count + upd_count    
    current_page = current_page + 1

  print "\n=> All done, total updated arks for LSDI = [%d]." % count
  sys.exit()

def process_page(page, results):
  all_count = 0;
  updatedcount = 0
  wrongfedorabasecount = 0
  na_count = 0
  for item in results:  
    targets = item['targets']
    for tg in targets:
      all_count = all_count + 1
      target_uri = tg['target_uri'] 
        
      if (target_uri.find("fedora")>0):
        tup = urlparse.urlparse(target_uri)      
        m = re.search('(.*):[0-9]+$', tup[1])
        url = m.group(1); # extract the domain without the port         
        m = re.search('fedora/get/(^/$)/?', tup[2])
        n = tup[2].split("/")
        old_url = tup[0] + "://" + tup[1]
        noid = item['pid']        
        if (old_url == old_fedora_base):  # only update the domain specified in the args 
          if (len(n) == 4 or (len(n) == 5 and n[4] == '')): # top level object REST format
            new_target_uri = new_fedora_base + "/fedora/objects/" + n[3]
            target_result = client.update_ark_target(noid, target_uri=new_target_uri)
          elif (len(n) == 5): # Datastream REST format
            new_target_uri = new_fedora_base + "/fedora/objects/" + n[3] + "/datastreams/" + n[4] + "/content"
            if(n[4] == "PDF"):
            	new_target_uri = new_target_uri + "?download=true"
            target_result = client.update_ark_target(noid, qualifier=n[4], target_uri=new_target_uri)

          updatedcount = updatedcount + 1 # Keep count of the database updates that were made.
        else: # The fedora base url does not match, so skip this ark
          wrongfedorabasecount = wrongfedorabasecount + 1
      else: # There is no 'fedora' pattern match for the target_uri
        na_count = na_count + 1
  print "   Page [%d] results: Updated[%d] WrongFedoraBase[%d] N/A[%d]." % (page, updatedcount, wrongfedorabasecount, na_count)
  return updatedcount
    
 
def validate(old_fedora_base, new_fedora_base):
  port_check = re.compile(".*([0-9]{4})$")  # regex pattern for port at end of string        
  if (old_fedora_base[0:4].lower() != 'http'):
    show_error('Error: first argument <old_base_url> must begin with "http"')
  elif (new_fedora_base[0:4].lower() != 'http'):
    show_error('Error: second argument <new_base_url> must begin with "http"')
  elif (port_check.match(old_fedora_base) is None):
    show_error('Error: first argument <old_base_url> must end with port number')
  elif (port_check.match(new_fedora_base) is None):
    show_error('Error: second argument <new_base_url> must end with port number')   
  
def show_error(err):
  print err
  usage()
  sys.exit() 
      
def usage():
  bold = "\033[1m"
  bold_off = "\033[0;0m"
  msg = '\n'
  msg = msg + bold + 'Description:' + bold_off + ' Update the lsdi domain arks for fedora 3.4 migration.\n'    
  msg = msg + bold + 'Usage:' + bold_off + ' migrate_lsdi_arks.py  <old_base_url> <new_base_url> <pid username> <pid password> <pid manager url>.\n'
  msg = msg + bold + 'Example:' + bold_off + ' migrate_lsdi_arks.py "https://dev11.library.emory.edu:8443" "https://dev11.library.emory.edu:8943" "username" "password" "https://testpid.library.emory.edu/"\n'    
  print msg
  sys.exit() 
    
if __name__ == "__main__":
    main()
    
    
