#!/usr/bin/env python
"""Attempts to merge the email and installs collections, by finding the
unique install record for email reporting / recording email address."""

from pprint import pprint
from .common import mongo

db = mongo()

def first_checkin(email_record):
    try:
        return min([c['time'] for c in email_record['checkins']])
    except KeyError:
        return None

def prev_install_record(time):
    try:
        return db.installs
            .find({"created_on": {"$lt": time}}, {"_id": 1, "created_on": 1})
            .sort({"created_on": -1})
            .limit(1)[0]
    except IndexError:
        return None

def next_install_record(time):
    try:
        return db.installs
            .find({"created_on": {"$gt": time}}, {"_id": 1, "created_on": 1})
            .sort({"created_on": 1})
            .limit(1)[0]
    except IndexError:
        return None

def closest_install_record(email_record):
    created = first_checkin(email_record)
    if not created:
        return None, None

    prev_record = prev_install_record(created)
    if prev_record:
        prev_created_on = prev_record['created_on']
        prev_delta = created - prev_created_on
        prev_values = prev_created_on, prev_delta

    next_record = next_install_record(created)
    if next_record:
        next_created_on = next_record['created_on']
        next_delta = next_created_on - created
        next_values = next_created_on, next_delta

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
        return None, None

mappings = []

for email_row in db.emails.find():
    install_time, time_delta = closest_install_record(email_row)
    if not install_time:
        continue
    mappings.append((email_row["_id"], install_time, time_delta))

pprint(mappings)
