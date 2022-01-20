import csv, sys
import datetime
from operator import attrgetter

from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

import time

# Set the given delay for waiting
delay = 2.5

# Get the login page
def getLogin(browser):
    browser.get("https://safeway.com/content/www/safeway/en/account/sign-in.html")

# Format the login info
def formatAccount(account):
    return account.split(':')

# Attempt to login to the account
def findAndLogin(username, password, browser):
    browser.find_element_by_id('label-email').send_keys(username)
    browser.find_element_by_id('label-password').send_keys(password, Keys.ENTER)

# Logout from the current account
def logOut(browser):
    # Uses the logout function on the site
    browser.execute_script('SWY.OKTA.signOut(event);')
    time.sleep(delay)

# Attempt to handle the change store location pop up
def handleNewStore(browser):
    browser.find_element_by_class_name('keep-store-btn').click()
    time.sleep(delay)
    
# Attempt to handle the change store location pop up
# Checks for presence of word Golden in current store name
def newHandleNewStore(browser):
    time.sleep(2)
    if 'Golden' in browser.find_element_by_id('currentlyAddress').text:
        browser.find_element_by_id('conflict-modal-firstfocus').click()
    else:
        browser.find_element_by_id('conflict-modal-secondfocus').click()
    time.sleep(0.5)
    browser.find_element_by_id('fulfillment-conflict-modal__button').click()
    time.sleep(delay)


# Coupons Page
COUPONS_URL = 'https://www.safeway.com/justforu/coupons-deals.html'

# Open the accounts file for login information
account_file = open('./accounts.txt', 'r')
account_list = []

# Create options for selenium
options = Options()
options.headless = True

# Banned phrases present in coupon names
# These usually aren't plain old free offers like we are
# Looking for
banned_phrases = [["Buy", "Get"], ["When","You","Buy"]]

# These aren't actually free
banned_coupons = ['FREE Lindt Chocolates (15.2oz bags): American Greetings', 'Free: Signature Select Food Protection and...',
'Free: Signature Care Hand Sanitizers or...'

]

# Using a set for no duplicates
allowed_coupons = set()
purged = set()

# Create the webdriver
browser = webdriver.Firefox(options=options)

# Store account names mapped to total amount of coupons clipped
result_dict = {}

# Any keywords to look for in coupon names
keywords = ["Free"]

# Store account names mapped to coupons that match keywords we were looking for
special_notes = {}

# Go through each account and clip the coupons
for line in account_file:
    try:
        counter = 0
        username, password = formatAccount(line)
        special_notes[username] = []
        getLogin(browser)
        time.sleep(delay)
        findAndLogin(username, password, browser)
        time.sleep(delay)
        browser.get(COUPONS_URL)
        time.sleep(delay)
        try:
            newHandleNewStore(browser)
            browser.get(COUPONS_URL)
            time.sleep(delay)
        except:
            pass
        
        # Try to click each coupon on the page, if none are left terminates the loop
        while True:
            # Loads more coupons on the page
            try:
                load_more = browser.find_element_by_css_selector('button.load-more')
                try:
                    load_more.click()
                # Tries to get rid of the new store pop up
                except ElementClickInterceptedException:
                    handleNewStore(browser)
                    continue
                time.sleep(0.1)
            # No more coupons to clip
            except NoSuchElementException:
                break
        # Select all buttons on the page
        button_array = browser.find_elements_by_css_selector('button.grid-coupon-btn')
        
        # Click each button on the page
        for button in button_array:
            try:
                button.click()
                time.sleep(0.1)
                counter += 1
            except ElementClickInterceptedException:
                browser.find_element_by_id('boxtopModalCancelBtn').click()
                time.sleep(1)
                button.click()
                time.sleep(1)
                counter += 1
        # Used for debugging, prints out the account name and number of coupons clipped
        print('{} : {}'.format(username, counter))
        
        # Records the account name and number of coupons clipped in result dictionary
        result_dict[username] = counter
        
        # Search for free offers
        for word in keywords:
            partial_matches = browser.find_elements_by_class_name('grid-coupon-heading-offer-price')
            for match in partial_matches:
                if word.lower() in match.text.lower():
                    parent = (match.find_element_by_xpath('..')).find_element_by_xpath('..').find_element_by_xpath('..').find_element_by_xpath('..').find_element_by_xpath('..')
                    desc_element = parent.find_element_by_class_name('grid-coupon-description-text-title').text
                    offer_matched = f'{match.text}: {desc_element}'
                    special_notes[username].append(offer_matched)
        
        logOut(browser)
        time.sleep(delay)
            
    except KeyboardInterrupt:
        print("Caught keyboard interupt, recording data so far")
        break
    except Exception as e:
        print(f'Exception caught while processing {username}')
        print(e)
        logOut(browser)
        time.sleep(delay)

# Close the browser and accounts file
browser.quit()
account_file.close()

# Record the given date and time
csv_date = datetime.datetime.now().strftime('%m_%d_%Y_%I-%M%p')

# Create a new csv and record the results of each account, and noting any skipped accounts
with open('./CouponStats/Coupon_Results_%s.csv' % csv_date, 'w') as csvfile:
    wcsv = csv.writer(csvfile, lineterminator='\n')
    csv_fields = ['Username', 'Coupon#']
    wcsv.writerow(csv_fields)
    for account, counters in result_dict.items():
        wcsv.writerow([account, counters])
    wcsv.writerow(['Special Notes'])
    for username, notes_list in special_notes.items():
        print(username, notes_list)
        try:
            temp_list = [username]
            remove_duplicates = list(set(notes_list))
            remove_duplicates.sort()
            
            # Remove things that aren't free
            for free_coupon in remove_duplicates:
                if free_coupon in purged or free_coupon in allowed_coupons:
                    continue
                if free_coupon in banned_coupons:
                    purged.add(free_coupon)
                    continue
                for phrase in banned_phrases:
                    full_match = 0
                    
                    for word in phrase:
                        if word.lower() in free_coupon.lower():
                            continue
                        else:
                            break
                    else:
                        purged.add(free_coupon)
                        full_match = 1
                    if full_match:
                        break
                else:
                    allowed_coupons.add(free_coupon)
            for purge in purged:
                try:
                    if purge in remove_duplicates:
                        remove_duplicates.remove(purge)
                except Exception as e:
                    print(e)
                    continue
             
            temp_list.extend(remove_duplicates)
            wcsv.writerow(temp_list)
        except Exception as e:
            print(e)
            wcsv.writerow([username, notes_list])
    # Add the coupons with banned keywords to the csv
    temp_row = ['Purged Coupons: ']
    temp_row.extend(purged)
    wcsv.writerow(temp_row)
    
    # Add the coupons that were validated to the csv
    temp_row = ['Allowed Coupons: ']
    temp_row.extend(allowed_coupons)
    wcsv.writerow(temp_row)