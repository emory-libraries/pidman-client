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

from eulcore.fedora import Repository
from eulcore.fedora.models import ContentModel
from eulcore.fedora.models import DigitalObject
from rdflib import Namespace

import urllib2
from urllib2 import URLError

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
  global new_url_base  # script first parameter. The base url to use before the <pid>. EX: https://marbl.library.emory.edu/collections/rushdie/documents/
  global db_username      # pidmanager username to connect to the REST Pid Client
  global db_password      # pidmanager password  to connect to the REST Pid Client
  global db_baseurl       # pidmanager url to connect to the REST Pid Client. EX: https://testpid.library.emory.edu/
  global fedora_url       #Fedora url to check objects. EX: https://fedora.library.emory.edu:8443/fedora/
  global fedora_username  #Fedora username to use for object checking. EX: fedoraAdmin
  global fedora_password  #Fedora password to use.

  
  for o, a in opts:   
    usage()
    sys.exit()
      
  if (len(args)==7):
    new_url_base = args[0]
    db_username = args[1]
    db_password = args[2] 
    db_baseurl = args[3]
    fedora_url = args[4]
    fedora_username = args[5]
    fedora_password = args[6]
      
    # validate that each arg starts with http and ends with a port number
    validate(new_url_base, fedora_url)     
  else:
    print '\nError: argument list incomplete. See usage example below.'
    usage()
    sys.exit()


  global repo
  repo = Repository(fedora_url,
                  username=fedora_username, password=fedora_password)
  

  #Pidman Client
  global client        
  client = PidmanRestClient(db_baseurl, db_username, db_password)
  connection = client._get_connection()
  
  current_page = 1
  count = 0
  max = 10000
    
  # search for existing arks by domain where type='ark', domain='LSDI'
  search_results = client.search_pids(type='ark', domain='Rushdie Collection', count=max)
  total_pages = search_results['page_count']
  page_link_1 = search_results['first_page_link']
  page_link = page_link_1[0:-1]
  
  print "\n=> Processing page[%d] that contains [%d] of a total of [%d] pages ..." %(current_page, max, total_pages)
  page_results = search_results['results']
  count = process_page(current_page, page_results)
  current_page = current_page + 1  
  while (current_page <= total_pages):
    search_results = client.search_pids(type='ark', domain='Rushdie Collection', page=current_page, count=max)
    page_results = search_results['results']    
    print "\n=> Processing page[%d] of [%d] that contains [%d] arks." \
          %(current_page, total_pages, max)
    upd_count = process_page(current_page, page_results)
    count = count + upd_count    
    current_page = current_page + 1

  print "\n=> All done, total updated arks for Rushdie = [%d]." % count
  sys.exit()

def process_page(page, results):
  updatedcount = 0
  for item in results:
      targets = item['targets']
      for tg in targets:
          access_uri = tg['access_uri']
          split_access_uri = access_uri.split("/")
          itemid = item['pid'] 
          full_pid = 'emory:' + itemid
          new_target_uri = new_url_base + full_pid
          obj = repo.get_object(pid=full_pid)

          if(obj.pid == "emory:1d17x" or obj.pid == "emory:1d196" or obj.pid == "emory:1d182" or obj.pid == "emory:1d1cg" or obj.pid == "emory:1d1bb"):
              #Object exists but is an item that we currently don't have access to - update it to point to fedora.
              target_result = client.update_ark_target(itemid, target_uri="https://fedora.library.emory.edu:8443/fedora/objects/" + full_pid, active=True)
          elif(obj.exists):
              #Plug objects into the webapp and make sure we don't get an error.
              returnCode = 0
              try:
                  HTTPresponse = urllib2.urlopen(new_target_uri)
                  htmlResult = HTTPresponse.read()
                  returnCode = HTTPresponse.code
              except URLError, e:
                  htmlResult = e.read()
                  returnCode = e.code
                  
              if(returnCode == 500):
                  #Object is not accessible in the webapp but is in fedora, update to point to fedora.
                  target_result = client.update_ark_target(itemid, target_uri="https://fedora.library.emory.edu:8443/fedora/objects/" + full_pid, active=True)
              elif(returnCode == 200):
                  #Object exists in fedora and is accessible in the webapp, update it to point to the documents of the webapp.
                  target_result = client.update_ark_target(itemid, target_uri=new_target_uri, active=True)
              else:
                  print "oooppss.... some unexpected return code has been detected."
          else:
              #Object doesn't exist (likely removed due to sensitivity concerns of the information). Leave its ARK, but mark inactive.
              target_result = client.update_ark_target(itemid, active=False)
          updatedcount = updatedcount + 1
          

  return updatedcount
    
 
def validate(new_url_base, fedora_url_base):
  if (new_url_base[0:5].lower() != 'https'):
    show_error('Error: first argument <new_base_url> must begin with "https"')
  elif (fedora_url_base[0:5].lower() != 'https'):
    show_error('Error: first argument <fedora_url> must begin with "https"')
  
def show_error(err):
  print err
  usage()
  sys.exit() 
      
def usage():
  bold = "\033[1m"
  bold_off = "\033[0;0m"
  msg = '\n'
  msg = msg + bold + 'Description:' + bold_off + ' Update the rushdie domain arks to the webapp.\n'    
  msg = msg + bold + 'Usage:' + bold_off + ' migrate_rushdie_arks.py  <new_base_url> <pid username> <pid password> <pid manager url> <fedora_url> <fedora_username> <fedora_password>.\n'
  msg = msg + bold + 'Example (quotes required):' + bold_off + ' migrate_lsdi_arks.py "https://marbl.library.emory.edu/collections/rushdie/documents/" "pid_manager_username" "pid_manager_password" "https://testpid.library.emory.edu/" "https://fedora.library.emory.edu:8443/fedora/" "fedoraAdmin" "fedora_password"\n'    
  print msg
  sys.exit() 
    
if __name__ == "__main__":
    main()
    
    
