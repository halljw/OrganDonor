#!/usr/bin/env python

import os, time
from optparse import OptionParser
from threading import Thread
from Queue import Queue

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import UnexpectedTagNameException
from selenium.common.exceptions import UnexpectedAlertPresentException

def get_center_names():
  """
  Crawls optn.translplant for names of all centers in each state.
  Stores names of all centers in centers.txt in comma-delimited pair with state:
    state,center
  """
  q = Queue()
  threads = []

  # Initiate thread for each state
  # each successful thread enqueues results of get_state_centers(i)
  for i in range(0,52):
    threads.append(Thread(target=enqueue_states, args=(q, i)))
    threads[i].start()
    time.sleep(1)

  # Join each thread
  for t in threads:
    t.join()

  # Gather results from queue
  with open('centers.txt', 'w') as f:
    while not q.empty():
      result = q.get()
      state, centers = result[0], result[1]

      # If there are no centers in a state, skip
      if not centers:
        continue

      # Write state, center results to centers.txt
      for center in centers:
        try:
          f.write('%s,%s\n' % (state, center))
        except UnicodeEncodeError:  # st mary's in michigan, ascii decode issue
          center = center.encode('ascii', 'ignore').decode('ascii')
          f.write('%s,%s\n' % (state, center))


def enqueue_states(q, state_i):
    q.put(get_state_centers(state_i))
 

def get_state_centers(state_i):
  """
  Crawls a given state specified by index number.
  Returns a tuple of the name of the state and all centers in that state
    ('state', [centers])
  """
  url = 'https://optn.transplant.hrsa.gov/data/view-data-reports/center-data/'
  options = Options()
  options.add_argument("--headless")

  browser = webdriver.Firefox(firefox_options=options)
  browser.get(url)
  assert "Center Data" in browser.title

  # Select state, click
  select_state = Select(browser.find_element_by_id("selectArea"))
  select_state.select_by_index(state_i)
  selected = select_state.first_selected_option
  state = selected.text
  browser.find_element_by_id('imgSubmit').click()

  # Get center options; If no center data available, close browser
  try:
    choose_center = Select(browser.find_element_by_id('slice2'))
  except NoSuchElementException:
    if verbose:
      print('[-] Data not available for %s' % state)
    browser.close()
    return None, None
  except UnexpectedAlertPresentException:
    if verbose:
      print('[-] Data not available for %s' % state)
    alert = browser.switch_to.alert
    alert.accept()
    browser.close()
    return None, None

  # Iterate through each hospital for that state (skip 'All Centers')
  centers = []
  for center_i in range(1, len(choose_center.options)):
    choose_center.select_by_index(center_i)
    selected = choose_center.first_selected_option
    centers.append(selected.text)

  # Close main browser when done
  browser.close()

  # Return ('state', [centers])
  if verbose:
    print('[+] Gathered centers for %s' % state)
  return (state, centers)


# Main method: crawl all centers in all states
if __name__=='__main__':

  parser = OptionParser('usage %prog')
  parser.add_option('-v', dest='verbose', action='store_true', help='make script verbose')
  options, args = parser.parse_args()
  verbose = options.verbose

  # If center names have not been collected already
  if not os.path.isfile('centers.txt'):
    if verbose:
      print('[+] Gathering centers for each state. Results will be output to "centers.txt"')
    get_center_names()
    if verbose:
      print('[+] All centers successfully gathered.')
  else:
    if verbose:
      print('[+] File "centers.txt" already exists.')
    

