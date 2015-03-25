#!/usr/bin/env python
"""Attempts to merge the email and installs collections, by finding the
unique install record for email reporting / recording email address."""

import sys
import argparse
from common import mongo
import pymongo

parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
parser.add_argument('--cutoff', '-c', type=int, default=60,
                    help="Maximum number of seconds that am email record " + 
                         "can differ from its closest install record and " +
                         "still be output.")
args = parser.parse_args()

db = mongo()

def first_checkin(email_record):
    try:
        return min([c['time'] for c in email_record['checkins']])
    except KeyError:
        return None

def prev_install_record(time):
    try:
        return (db.installs
            .find({"created_on": {"$lt": time}}, {"_id": 1, "created_on": 1})
            .sort("created_on", pymongo.DESCENDING)
            .limit(1)[0])
    except IndexError:
        return None

def next_install_record(time):
    try:
        return (db.installs
            .find({"created_on": {"$gt": time}}, {"_id": 1, "created_on": 1})
            .sort("created_on", pymongo.ASCENDING)
            .limit(1)[0])
    except IndexError:
        return None

def closest_install_record(email_record):
    created = first_checkin(email_record)
    if not created:
        return None, None, None

    prev_record = prev_install_record(created)
    if prev_record:
        prev_created_on = prev_record['created_on']
        prev_delta = created - prev_created_on
        prev_id = prev_record["_id"]
        prev_values = prev_created_on, prev_delta, prev_id

    next_record = next_install_record(created)
    if next_record:
        next_created_on = next_record['created_on']
        next_delta = next_created_on - created
        next_id = next_record['_id']
        next_values = next_created_on, next_delta, next_id

    if next_record and prev_record:
        if prev_delta < next_delta:
            return prev_values
        else:
            return next_values
    elif prev_record:
        return prev_values
    elif next_record:
        return next_values
    else:
        return None, None, None

mappings = []
ids = []

for email_row in db.emails.find():
    install_time, time_delta, install_id = closest_install_record(email_row)
    if not install_time:
        continue
    delta_secs = time_delta.microseconds / float(1000)
    if delta_secs > args.cutoff:
        continue
    mappings.append((email_row["_id"], time_delta.microseconds / float(1000), install_id))

for email, diff, an_id in mappings:
    print "{} {}".format(email, an_id)
