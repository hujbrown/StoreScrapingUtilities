from bs4 import BeautifulSoup
import csv
import datetime
from operator import attrgetter
import requests
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

delay = 2

caps = DesiredCapabilities().FIREFOX
caps["pageLoadStrategy"] = "eager"  # interactive

# Store the data of an account
class SWayAccount:
    def __init__(self, username, rewards, points, expiring_rewards):
        self.username = username
        self.rewards = int(rewards)
        self.points = int(points)
        self.expiring_rewards = int(expiring_rewards)
    def __str__(self):
        return self.username
    def ToRow(self):
        seperator = ','
        field_list = [self.username, self.rewards, self.points, self.expiring_rewards]
        return field_list

def rewardsSort(acct):
    return (acct.rewards, acct.points)

# Get the login page
def getLogin(browser):
    browser.get("https://safeway.com/content/www/safeway/en/account/sign-in.html")

# Format the login info
def formatAccount(account):
    return account.split(':')

# Attempt to login to the account
def findAndLogin(username, password, browser):
    element = WebDriverWait(browser, 10).until(
    EC.presence_of_element_located((By.ID, 'label-email')))
    
    browser.find_element_by_id('label-email').send_keys(username)
    browser.find_element_by_id('label-password').send_keys(password, Keys.ENTER)
    
    element = WebDriverWait(browser, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, 'menu-nav__profile-button-sign-in-up')))
    
# Get the rewards listing page of an account
def getRewardsPage(browser):
    browser.get("https://www.safeway.com/customer-account/rewards")

# Get the current rewards points, points progress, and expiring points
def getRewardsValues(browser):
    
    # Wait until the element loads on the page
    element = WebDriverWait(browser, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, 'span.curr-points')))
    time.sleep(delay)
    
    reward_points = browser.find_element_by_css_selector('span.curr-points')
    reward_balance = browser.find_element_by_css_selector('span.rewards-balance')
    
    Rewards = reward_balance.text
    Points = reward_points.text
    # This isn't currently available for scraping at the moment, leaving it as an options
    # In case it returns
    Expired = 0
    return [Rewards, Points, Expired]

# Logout from the current account
def logOut(browser):

    # Uses the logout function on the site
    browser.execute_script('SWY.OKTA.signOut(event);')
    
    # Wait until the sign in element appears
    element = WebDriverWait(browser, 10).until(
    EC.text_to_be_present_in_element((By.CLASS_NAME, 'menu-nav__profile-button-sign-in-up'), 'Sign In / Up'))
    
# Attempt to handle the change store location pop up
def handleNewStore(browser):
    browser.find_element_by_class_name('keep-store-btn').click()
    
# Login and record rewards values for a given account
def processAccount(browser, username, password):
    # Login
    getLogin(browser)
    time.sleep(delay)
    findAndLogin(username, password, browser)
    # Get Rewards
    getRewardsPage(browser)
    
    values_list = getRewardsValues(browser)
    
    # Log Out
    logOut(browser)
    return values_list

    
    
    
# Main code

# Open the accounts file for login information
account_file = open('./accounts.txt', 'r')
account_list = []

# Create options for selenium
options = Options()

# Option to run headless
options.headless = True

# Create the webdriver
browser = webdriver.Firefox(capabilities=caps, options=options)

# If a user can't be read, add it to the skipped users list
skipped_users = []

# Go through each account, and record the values on the site
for line in account_file:
    try:
        username, password = formatAccount(line)
        values = processAccount(browser, username, password)
        account_list.append(SWayAccount(username, values[0], values[1], values[2]))
        time.sleep(delay)
    except KeyboardInterrupt:
        print("Caught keyboard interupt, recording data so far")
        break
    except:
        try:
            time.sleep(1)
            values = processAccount(browser, username, password)
            account_list.append(SWayAccount(username, values[0], values[1], values[2]))
            time.sleep(delay)
        except KeyboardInterrupt:
            print("Caught keyboard interupt, recording data so far")
            break
        except:
            skipped_users.append(username)
            browser.execute_script('SWY.OKTA.signOut(event);')
            continue

# Close the browser and accounts file
browser.quit()
account_file.close()

# Sort the account list by rewards, then points
account_list = sorted(account_list, key=attrgetter('rewards', 'points'), reverse=True)

# Record the given date and time
csv_date = datetime.datetime.now().strftime('%m_%d_%Y_%I-%M%p')

# Create a new csv and record the results of each account, and noting any skipped accounts
with open('./Results/safeway_Results_%s.csv' % csv_date, 'w') as csvfile:
    wcsv = csv.writer(csvfile, lineterminator='\n')
    csv_fields = ['Username', 'Rewards', 'Points', 'Expiring']
    wcsv.writerow(csv_fields)
    for account in account_list:
        wcsv.writerow(account.ToRow())
    if skipped_users:
        wcsv.writerow(['Skipped Accounts'])
        for user in skipped_users:
            wcsv.writerow([user])

# Print out any skipped accounts, mainly for debugging running manually
if skipped_users:
    print(skipped_users)