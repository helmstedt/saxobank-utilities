# saxobank-utilities

A script for extracting transaction data from Saxo Bank
==========================================

This script  will let you extract transaction data from Saxo Bank (see https://www.home.saxo/). You can modify the script to perform other API calls to Saxo Bank. Use your browser developer tools or https://www.developer.saxo/openapi/learn to get to know the calls you can perform.

Getting started
===============

For the script to work, make sure that you have less than six already approved devices for Saxo Bank. Also, you should be receiving two factor codes by phone text message (SMS).

Run `saxo-transactions.py` with the following parameters:

`saxo-transactions.py -f -u USERNAME -p PASSWORD -s yyyy-mm-dd`

For example:

`saxo-transactions.py -f -u 1234567 -p CorrectHorseBatteryStaple -s 2020-01-01`

This will get you all transactions since January 1, 2020. 

The script will prompt you for a two factor code to enter during the first run.

On your first run, a pickle file with a randomly generated identity will be saved to the same folder as the script.

For subsequent runs, ditch the -f parameter. The script will load the pickle file and you will not have to enter any more two factor codes. Like so:

`saxo-transactions.py -u 1234567 -p CorrectHorseBatteryStaple -s 2020-01-01`

If, for some reason, the script stops working. Try running the script with the `-f` parameter again to log in using a two factor code and generate a new pickle file.

Additional paramters for the script are:

`-e`: Set an end date for the transaction data to fetch.
`-d`: Set a device name. Lets you identify the script logon when managing connected devices in your Saxo Bank account.

Questions
=========

Feel free to get in touch. My contact information is available on https://helmstedt.dk.
 
