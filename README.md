# Echo2Google

Program that moves items from Amazon Echo's to-do list to Google Calendar

Echo2Google monitors Amazon Echo's to-do list for items.  When it finds a new item, it moves the item 
to a Google calendar.  The Google calendar API handles natural language entries so that you can say
things like "Turn in TPS report tomorrow at 5pm" and it will create an entry "Turn in TPS report" with
a start time of tomorrow at 5pm.

In order to run Echo2Google, you will need to sign up as a google developer(free) so that you can gain
access to a developer account.  The developer account allows you to get a "Client ID" which is use to
track the Google API usage.  You'll need to download the "client_secrets.json" file which contains your
developer client ID and client secret.  For more information on setting up your developer console, see
this website

https://developers.google.com/google-apps/calendar/firstapp

You will need to follow the instructions on the "/firstapp/Prerequisites" tab to setup the developer
console and obtain the client ID.  You will also need to follow the instructions in "/firstapp/Set up a 
Client Library" to download the google api python extension.

# Requirements
PyEcho https://github.com/scotttherobot/PyEcho
Google API https://developers.google.com/google-apps/calendar/setup
pytz: install from easy_install
dateutil: install from repo
gflags: install from repo
beautifulsoup: install from repo
bs4: install from repo

# Usage
Usage:  ./Echo2Google.py  -[u:p:j:d:]
   -u: Amazon username
   -p: Amazon password
   -j: Google client secrets json file
   -d: delay in seconds between each check for new tasks (default 30)

   If no username/password is given, this program will ask for them.
