#!/usr/bin/env python
"""Attempts to merge the email and installs collections, by finding the
unique install record for email reporting / recording email address."""

import sys
import argparse
from pprint import pprint
from common import mongo
import datetime
import pymongo

parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
parser.add_argument('--verbose', '-v', default=False, action="store_true")
parser.add_argument('--days', '-d', default=3, type=int,
                    help="Filter value, where if a user is not active at " +
                         "every (this many) days, they're excluded from the " +
                         "results.")
parser.add_argument('--heartbeat', '-b', default=3600, type=int,
                    help="The minimum number of seconds that occur between " +
                         "each user's heartbeat.")
parser.add_argument('--email', '-e', default=None,
                    help="If provided, specifies to only attempt to match " +
                         "a single email address.")
args = parser.parse_args()

def debug(msg):
    if args.verbose:
        print msg

db = mongo()

# Store mappings of install_id -> (email, num_pws)
done_users = {}

# Store mappings of email -> lists of date ranges that the user should not be active during
user_deadspots = {}

# Filter users out that are not sufficiently active
threshold_diff = datetime.timedelta(days=args.days)

# The last date we want to consider for the study
max_date = datetime.datetime(2014, 12, 1)

heartbeat_delta = datetime.timedelta(seconds=args.heartbeat)

email_records = {r['_id']: r for r in db.emails.find() if r['_id'] not in ['test@test.test', 'snyderp@gmail.com']}

installs = {r['_id']: r for r in db.installs.find()}
install_count = len(installs)

for email, row in email_records.items():
    times = sorted([c['time'] for c in row['checkins'] if c['time'] < max_date])
    if len(times) < 2:
        del email_records[email]
        continue 

    deadspots = []
    time_diffs = []
    last_time = None
    for time in times:
        if last_time:
            time_diffs.append(time - last_time)
            deadspots.append((last_time + heartbeat_delta, time - datetime.timedelta(seconds=60)))
        last_time = time

    if max(time_diffs) > threshold_diff:
        debug("Excluding {} from study, time diff = {}".format(email, max(time_diffs)))
        del email_records[email]
        continue 

    user_deadspots[email] = deadspots

all_mapped_users = set(user_deadspots.keys())
last_try_count = None

while not last_try_count or last_try_count != len(email_records):
    last_try_count = len(email_records)
    debug("Progress: {} / {}\n\n".format(len(done_users), install_count))
    for install_id, data_row in installs.items():
        if install_id in done_users:
            continue
        checkin_times = [c['date'] for c in data_row['pws']]
    
        # If it doesn't look like this person used the app too much, we ignore them, at least for now
        if len(checkin_times) < 10:
            continue
   
        possible_emails = [] 
        for email, record in email_records.items():
            deadzones = user_deadspots[email]
            hard_break = False
    
            for start_datetime, end_datetime in deadzones:
                if hard_break:
                    break
    
                for checkin_time in checkin_times:
                    if checkin_time > start_datetime and checkin_time < end_datetime:
                        # print "{} < {} < {} for {} / {}".format(start_datetime, checkin_time, end_datetime, install_id, possible_email)
                        hard_break = True
                        break

            if not hard_break:
                possible_emails.append(email)
    
        if len(possible_emails) == 0:
            debug("Could not find a match for install_id {}".format(install_id))
            continue
    
        if len(possible_emails) != 1:
            debug("Too many possible matches for {} -> {}".format(install_id, possible_emails))        
            continue
   
        del installs[install_id] 
        del email_records[possible_emails[0]]
        done_users[install_id] = (possible_emails[0], len(data_row['pws']))

# At this point, we've completed all the garanteed mappings that we can probably get.
# now we need to rely on more heuristic based techniques.  We go through now and
# find the closest matching for each reamining install id.  We give the closest match
# away at each step.  So, this will take a while...
soonest_match_time = None
match_time_cutoff = datetime.timedelta(seconds=30)
while (not soonest_match_time) or (len(installs) > 0 and soonest_match_time < match_time_cutoff):
    soonest_match_install_id = None
    soonest_match_email = None
    soonest_match_time = None
    soonest_registration_time = None
    soonest_checkin_time = None

    for install_id, install_row in installs.items():
        registered_time = install_row['created_on']
        for email, email_row in email_records.items():
            earliest_checkin = email_row['checkins'][0]['time']

            # Since we register ourselves with the install table first, an earlier
            # email record means no match for sure
            if earliest_checkin < registered_time:
                continue
   
            if not soonest_match_time:
                soonest_match_time = earliest_checkin - registered_time
                soonest_match_install_id = install_id
                soonest_match_email = email
                soonest_registration_time = registered_time
                soonest_checkin_time = earliest_checkin
                continue
            
            if earliest_checkin - registered_time < soonest_match_time: 
                soonest_match_time = earliest_checkin - registered_time
                soonest_match_install_id = install_id
                soonest_match_email = email
                soonest_registration_time = registered_time
                soonest_checkin_time = earliest_checkin
                continue

    if soonest_match_time and soonest_match_time < match_time_cutoff:
        del email_records[soonest_match_email]
        done_users[soonest_match_install_id] = (soonest_match_email, len(installs[soonest_match_install_id]['pws']))
        del installs[soonest_match_install_id]
        debug("Found mapping: {} -> {} ({} vs {} - {})".format(soonest_match_install_id, soonest_match_email, soonest_checkin_time, soonest_registration_time, soonest_match_time))
        continue

    debug("Still not able to find pairings for remaining install ids: {}".format(installs.keys()))
    break

for install_id, (email, num_pw) in done_users.items():
    print "{} {} {}".format(email.lower(), install_id, num_pw)

# from pprint import pprint
# print "\nUNMAPPED\n-----"
# print "Unable to map {} emails".format(len(email_records))

