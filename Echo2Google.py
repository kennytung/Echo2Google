#!/usr/bin/python

import sys, getpass, getopt
import time, datetime, dateutil.parser, pytz
import gflags
import httplib2

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

FLAGS = gflags.FLAGS

# setup the PyEcho path, you will need to change this to match your
# PyEcho install directory
sys.path.append('../PyEcho')
try:
    import PyEcho
except ImportError:
    print ''
    print 'Cannot import PyEcho, please download PyEcho from'
    print 'https://github.com/scotttherobot/PyEcho'
    print ''
    print 'You will need to setup PYTHONPATH so that python can import PyEcho.'
    print 'You can also do it in code by changing sys.path.append(...)'
    sys.exit(0)

# Log in to Google to access the calendar API.  The login code has been
# lifted from https://developers.google.com/google-apps/calendar/instantiate
# and uses the OAuth 2.0 method of authenication.  You will need to provide your
# own client_id and client_secret.  The developer client credentials should
# be passed in as an argument pointing to the client_secret.json file that you
# can download from the Google Developers Console, under APIs & auth, Credentials.
# Do not share your client secret as that can lead to others spoofing your ID and
# use your resources.
def googleapilogin(secretsfile):
    # TODO:  need to get rid of this heavy handed way of checking
    #        if the log in is successful.  Right now, if anything
    #        throws anything, the login is consider not successful.
    service = None
    try:
        FLOW = flow_from_clientsecrets(secretsfile,
                scope='https://www.googleapis.com/auth/calendar')

        storage = Storage('calendar.dat')
        credentials = storage.get()

        if credentials is None or credentials.invalid == True:
            credentials = run(FLOW, storage)

        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build(serviceName='calendar', version='v3', http=http)
    except Exception, e:
        print ''
        print 'Google login exception: '+str(e.__class__)+': '+str(e)
        print ''
        print 'Could not log in to Google API services.'
        print 'Check your client_secrets file to make sure it'
        print 'is correct.  Also check that you have enabled'
        print 'the calendar API in your google developer console.'
        print 'Check this website for more details on how to setup'
        print 'your google developer calendar API access.'
        print 'https://developers.google.com/google-apps/calendar/firstapp'
        print ''
        raise ReferenceError('GoogleAPILoginException')

    return service 

def get_calID(calendar, service) :
    calID = None
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'].lower().strip() == calendar.lower().strip():
                calID = calendar_list_entry['id']
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

    if calID == None:
        # Could not find the requested calendar, so exit
        print ''
        print 'Could not find the calendar \"%s\"' % calendar
        print ''
        raise ReferenceError('CannotGetCalendarID')

    return calID

def usage() :
    print ''
    print 'Usage: ', sys.argv[0], ' -[u:p:j:d:]'
    print '   -u: Amazon username'
    print '   -p: Amazon password'
    print '   -j: Google client secrets json file'
    print '   -d: delay in seconds between each check for new tasks (default 30)'
    print ''
    print '   If no username/password is given, this program will ask for them.'
    print ''
    sys.exit(0)

def main() :
    email = None
    password = None
    clientsecretsfile = None
    delay = 30

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'u:p:j:d:')
    except getopt.GetoptError, err:
        print str(err)
        usage()

    for o, a in opts:
        if o == '-u':
            email = a
        elif o == '-p':
            password = a
        elif o == '-j':
            clientsecretsfile = a
        elif o == '-d':
            delay = int(a)
        else:
            usage()

    if clientsecretsfile == None:
        print ''
        print 'Missing client secrets file.  You need to have a Google developer'
        print 'account and have a client secrets json file.  See the following'
        print 'website for detail on how to setup access to Google developers'
        print 'account and the calendar API.'
        print 'https://developers.google.com/google-apps/calendar/firstapp'
        usage()

    if email == None:
        email = raw_input("Amazon username: ")
    if password == None:
        password = getpass.getpass()

    # See if I can log in to amazon
    echo = PyEcho.PyEcho(email, password)

    if not echo.loginsuccess:
        print ''
        print 'Could not log in to Amazon Echo webservice'
        print 'Wrong username/password?'
        print ''
        sys.exit(0)

    # See if I can log in to google
    try:
        service = googleapilogin(clientsecretsfile)
    except ReferenceError, err:
        # can't log in, so exit
        sys.exit(0)

    # TODO: Right now I'm only looking for the "Alexa" calendar.  Later, this
    #       will need to change to user define
    try:
        calID = get_calID('Alexa', service)
    except ReferenceError, err:
        # can't get calendar ID, so exit
        sys.exit(0)

    # If I reach this point, I know that I could:
    # Log in to Amazon
    # Log in to Google
    # Get the calendar ID
    #
    # I will now throw away the service object because I won't be able to hold onto the
    # token for that long anyway.  I will get a new token when I need to add tasks into Google.
    service = None

    # main loop, run forever
    while True:
        tasks = echo.tasks()
        for t in tasks:
            print 'Found task item: '+t['text']
            try:
                service = googleapilogin(clientsecretsfile)
                #TODO: fix hard code 'alexa' here
                calID = get_calID('Alexa', service)
                calentry = service.events().quickAdd(calendarId=calID, text=t['text']).execute()
            except ReferenceError, err:
                print err
                # something went wrong with logging into Google, so quit.
                # TODO: decide if the program should quit, maybe it should retry
                sys.exit(0)
            
            # The new task was added to google successfully, but google quickadd allows any
            # entry to be added even if it doesn't have a time component.  In that case, the
            # entry will be given the current time as a start time.  I don't think I should 
            # add tasks that doesn't have a time component to google because calendar items
            # should always have a set time.  So I will filter out these enties by checking
            # to see if 'created' and 'start' is the same time.  If they are, then the time 
            # component is missing and I will delete the entry from google.
            created=dateutil.parser.parse(calentry['created'])
            if 'date' in calentry['start']:
                # Google treats entries with only a date component as all day events, which
                # only has a 'date' in the 'start' field.  Need to add the timezone into the
                # datetime object so that timedelta can be properly calculated.
                start=dateutil.parser.parse(calentry['start']['date'])
                start=start.replace(tzinfo=pytz.timezone(time.tzname[0]))
            else:
                start=dateutil.parser.parse(calentry['start']['dateTime'])
            timedelta = (start-created).total_seconds()
            if timedelta < 60:
                # if the time difference is less than 60 seconds, assume this is a mistake
                # and delete the entry from google
                print 'Ignored to-do item [',t['text'],'] due to missing time component.'
                service.events().delete(calendarId=calID, eventId=calentry['id']).execute();
            else:
                print 'Successfully added to-do item [',calentry['summary'],'] with start time on',start

            res = echo.deleteTask(t)
            # TODO: do I need to check the responds from Amazon?
        
        time.sleep(delay)

if __name__ == "__main__" :
    main()
