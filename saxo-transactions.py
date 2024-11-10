# -*- coding: utf-8 -*-
# Author: Morten Helmstedt. E-mail: helmstedt@gmail.com
"""This script logs into a Saxo Bank account and performs a query to extract transactions.
For the script to work, make sure that you have less than six already approved devices for
Saxo Bank. Also, you should be receiving two factor codes by phone text message."""

import argparse
import base64
from datetime import datetime
from datetime import date
import json
import pickle
import requests
import secrets
import string
import sys

### INITIALIZE AND VALIDATE PARSER ARGUMENTS ###

IDENTITY_FILENAME = 'identity.pickle'
TODAY = date.today()
TODAY_STRING = datetime.strftime(TODAY, '%Y-%m-%d')

# Initialize requests session and set user agent
# I suspect that Saxo Bank requires a recent browser. If the program fails, try visiting a site
# in an updated browser with developer tools open and paste the user agent value from your browser below.
session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; rv:122.0) Gecko/20100101 Firefox/122.0'

# Define parser arguments
parser = argparse.ArgumentParser(description='Fetch transaction data from Saxo Bank')
parser.add_argument('-f', '--firstrun', help='Run the script for the first time and login using two factor login', action='store_true')
parser.add_argument('-u', '--user', help='Saxo Bank user name', type=str, required=True)
parser.add_argument('-p', '--password', help='Saxo bank password', type=str, required=True)
parser.add_argument('-s', '--startdate', help='Get data from this date, format yyyy-mm-dd', type=str, required=True)
parser.add_argument('-e', '--enddate', help='Get data to and including this date, format yyyy-mm-dd, default is today', type=str, default=TODAY_STRING)
parser.add_argument('-d', '--devicename', help='Device name, default is SaxoPython', type=str, default='SaxoPython')
args = parser.parse_args()

# Set arguments as variables
user = args.user
password = args.password
device_name = args.devicename
startdate = args.startdate
enddate = args.enddate

# Date argument validation
try:
    start_date_date = datetime.strptime(startdate, '%Y-%m-%d').date()
    end_date_date = datetime.strptime(enddate, '%Y-%m-%d').date()
    if start_date_date > TODAY:
        sys.exit('Error: Your start date cannot be after today. Exiting.')
    elif end_date_date > TODAY:
        sys.exit('Error: Your end date cannot not be after today. Exiting.')
    elif start_date_date > end_date_date:
        sys.exit('Error: Your start date must not be after your end date. Exiting.')
except ValueError:
    sys.exit('Error: Start or end date in invalid format. Format must be yyyy-mm-dd with no quotes. Exiting.')

# If the first run parameter is set, create (minimal) unique identity string in order
# to later remember the device and avoid two factor authentification. The identity 
# string is pickled and saved.
if args.firstrun:
    print('You are running the script for the first time. Creating and saving identity file.')
    identifier = ''
    for i in range(3):
        identifier += ''.join(secrets.choice(string.digits) for i in range(10))
        if i < 2:
            identifier += '-'

    identity = '{\"identifier\":\"' + identifier + '\",\"metadata\":\"\"}'

    with open(IDENTITY_FILENAME, 'wb') as identity_file:
        pickle.dump(identity, identity_file)
        print(f'Identity file saved in script directory as {IDENTITY_FILENAME}.')
# If the first run parameter is not set, try to load and unpickle the identity file.
else:
    try:
        with open(IDENTITY_FILENAME, 'rb') as identity_file:
            identity = pickle.load(identity_file)
    except FileNotFoundError:        
        sys.exit('Error: The script was launched without the -f/--firstrun parameter, but no identity file was found. Use the -f parameter and try again.')


### LOGIN PROCEDURE ###
print('Starting login procedure...')

# Step one: Fetch login page and get correlation id from page source
step_one = session.get('https://www.saxoinvestor.dk/Login/da')
step_one_text = step_one.text
search_string = '"correlationId":"'
start_of_correlation_id = step_one_text.index(search_string)+len(search_string)
end_of_correlation_id = step_one_text.index('"', start_of_correlation_id)
correlation_id = step_one_text[start_of_correlation_id:end_of_correlation_id]

# Insert correlation id in state string and encode it as base 64 for later use
state_string = '{"appId":"investor","correlationId":"' + correlation_id + '"}'
state_string_b64_encoded = base64.b64encode(bytes(state_string, 'utf-8')).decode()

# Step two: Start authentication part one of X
login_url = 'https://www.saxoinvestor.dk/am/json/realms/root/realms/dca/authenticate?authIndexType=service&authIndexValue=authn-web-v6'

step_two = session.post(login_url)
step_two_json = step_two.json()

# Step three: Prepare data structure and perform authentication part two of a possible five
step_three_json_struct = step_two_json
step_two_json['callbacks'][0]['input'][0]['value'] = user
step_two_json['callbacks'][1]['input'][0]['value'] = "https://www.saxoinvestor.dk/investor"
step_two_json['callbacks'][2]['input'][0]['value'] = "SaxoInvestor"
step_two_json['callbacks'][3]['input'][0]['value'] = identity

step_three = session.post(login_url, json=step_two_json)
step_three_json = step_three.json()

# Step four: Prepare data structure and perform authentication part three of a possible five
step_three_json['callbacks'][1]['input'][0]['value'] = user
step_three_json['callbacks'][2]['input'][0]['value'] = password

step_four = session.post(login_url, json=step_three_json)
step_four_json = step_four.json()

if 'stage' in step_four_json:
    if step_four_json['stage'] == 'retryCredentialsPage':
        sys.exit('Error: Login failed, probably due to a wrong username/password combination. Please double check and try again.')

# With an unknown device, the user is asked for a two factor login code
if args.firstrun:
    print('As this is your first run, you must enter a two factor code from your phone.')
    # Step five: Enter two factor code and perform authentication part four of a possible five
    two_factor_code = input('Enter two factor code (six digits): ')
    step_four_json['callbacks'][0]['input'][0]['value'] = two_factor_code

    step_five = session.post(login_url, json=step_four_json)
    step_five_json = step_five.json()

    # Step six: Save device to perform authentication part five of a possible five
    step_five_json['callbacks'][0]['input'][0]['value'] = device_name

    step_six = session.post(login_url, json=step_five_json)
    step_six_json = step_six.json()
    token_id = step_six_json['tokenId']
else:
    token_id = step_four_json['tokenId']

# Authenticate
auth_url = 'https://www.saxoinvestor.dk/am/oauth2/realms/root/realms/dca/authorize'

auth_data = f'csrf={token_id}&scope=openid%20profile%20openapi%20fr%3Aidm%3A*&response_type=code&client_id=SaxoInvestorPlatform&redirect_uri=https%3A%2F%2Fwww.saxoinvestor.dk%2Fapi%2Flogin%2Fcode&decision=allow&state={state_string_b64_encoded}'
session.headers['Content-Type'] = 'application/x-www-form-urlencoded'

authenticate = session.post(auth_url, data=auth_data)
authenticate_json = authenticate.json()

del session.headers['Content-Type']

# Open app website and extract API bearer token
beater_token_code = authenticate_json['code']
bearer_token_url = f'https://www.saxoinvestor.dk/showapp?code={beater_token_code}&state={state_string_b64_encoded}'

get_bearer_token = session.get(bearer_token_url)
get_bearer_token_text = get_bearer_token.text

search_string = ',"idToken":"'
start_of_bearer_token = get_bearer_token_text.index(search_string)+len(search_string)
end_of_bearer_token = get_bearer_token_text.index('"', start_of_bearer_token)
bearer_token = get_bearer_token_text[start_of_bearer_token:end_of_bearer_token]
bearer_token_string = 'Bearer ' + bearer_token

### PERFORM API CALLS ###
# Documentation at https://www.developer.saxo/openapi/learn
print('Login successful (I think). Getting transaction data.')

# Set bearer token as header
session.headers['Authorization'] = bearer_token_string

# API request to get Client Key which is used for most API calls
# See https://www.developer.saxo/openapi/learn/the-tutorial for expected return data
url = 'https://www.saxoinvestor.dk/openapi/port/v1/clients/me'
get_client = session.get(url)
clientdata = get_client.json()
clientkey = clientdata['ClientKey']

# Extract transactions
url = f'https://www.saxotrader.com/openapi/hist/v1/transactions?ClientKey={clientkey}&FromDate={startdate}&ToDate={enddate}'
saxo_transactions = session.get(url)
if saxo_transactions.status_code == 200:
    print('Looks like your transactions were extracted. Edit the script to process your data.')
    saxo_transactions_json = saxo_transactions.json()
else:
    print('Extracting your transactions failed for some reason. Sorry about that.')

# Other example API calls
# Create random string context_id
context_id =  ''.join(secrets.choice(string.digits) for i in range(10))
# Create reference id, add one to reference_id for each api call
reference_id = 1

# List accounts
print('Getting list of accounts...')
url = 'https://www.saxotrader.com/openapi/port/v1/accounts/subscriptions'
json = {
	"Arguments": {
		"ClientKey": clientkey
	},
	"ContextId": context_id,
	"ReferenceId": str(reference_id)
}

saxo_accounts = session.post(url, json=json)
if saxo_accounts.status_code == 201:
    print('Got your list of accounts')
    saxo_accounts_json = saxo_accounts.json()

    account_keys = []
    for account in saxo_accounts_json['Snapshot']['Data']:
        account_keys.append(account['AccountKey'])
   
    # Extract positions
    print('Extracting account positions...')
    url = 'https://www.saxotrader.com/openapi/port/v1/netpositions/subscriptions'
    positions = []
    for account_key in account_keys:
        reference_id += 1
        json = {
            "Arguments": {
                "ClientKey": clientkey,
                "AccountKey": account_key,
                "FieldGroups": [
                    "NetPositionView",
                    "NetPositionBase",
                    "DisplayAndFormat",
                    "ExchangeInfo",
                    "Greeks",
                    "SinglePosition",
                    "SinglePositionBase",
                    "SinglePositionView",
                    "UnderlyingDisplayAndFormat"
                ],
                "PriceMode": None
            },
            "ContextId": context_id,
            "ReferenceId": str(reference_id)
        }
        account_positions = session.post(url, json=json)
        if account_positions.status_code == 201:
            account_positions_json = account_positions.json()
            positions.append(account_positions_json)
            position_success = True
        else:
            print('Failed to get positions for at least one account. Sorry about that')
            position_success = False
            break
    if position_success:
        print('Looks like your positions were extracted. Edit the script to process your data.')
else:
    print('Failed to get your list of accounts. Sorry about that')