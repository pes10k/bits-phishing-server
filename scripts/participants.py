#!/usr/bin/python
"""
CLI for interacting with the MongoDB instance that stores current plugin
instance.  More useful information / options are available with --help
"""

import argparse
import datetime
import os
import sys
import json
from common import mongo

parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
parser.add_argument("--days", "-d", type=int, default=2,
                    help="The number of days used as a threshold for " +
                         "measuring activeness etc.")
parser.add_argument("--active", "-a", action="store_true",
                    help="Prints statistics about how many plugins are " +
                         "currently active. A plugin is considered active " +
                         "if it has checked in during the last 48 hours.")
parser.add_argument("--inemails", "-e", action="store_true",
                    help="Prints the email addresses of all participants " +
                         "that have reported in since the threshold.")
parser.add_argument("--outemails", "-o", action="store_true",
                    help="Prints the email address of all participants " +
                         "that have not reported since the theshold date.")
parser.add_argument("--group", "-g", default=None,
                    help="If provided, lists all install ids that are " +
                         "active and ,assigned to a given group.")
parser.add_argument("--misses", "-m", action="store_true",
                    help="Print out a list of accounts that have " +
                         "participated but which have a gap of greater than " +
                         "{--days} in their reporting.")
parser.add_argument("--passwords", "-p", action="store_true",
                    help="Print out the number of passwords that have been " +
                         "entered by participants.  Can be filtered down " +
                         "with the {--group} and {--domains} parameters.")
parser.add_argument("--domains", action="store_true",
                    help="Filters down password matches to only include " +
                         "passwords entered on domains we log users out of.")
parser.add_argument("--hits", action="store_true",
                    help="Print out a list of email accounts that have " +
                         "phoned home at least ever {--days} days, and " +
                         "thus are eligable to be included in the final " +
                         "count.")
args = parser.parse_args()

db = mongo()
threshold_diff = datetime.timedelta(days=args.days)
threshold = datetime.datetime.now() - threshold_diff


def watched_domains():
    path_to_rules_file = os.path.join("..", "files", 'cookie-rules.json')
    domains = None
    with open(path_to_rules_file, 'r') as h:
        domains = [r['domain'].strip(".") for r in json.load(h)]
    return domains


def is_active(record):
    checkins = record["checkins"]
    if len(checkins) == 0:
        return False
    latest_checkin = checkins[-1]['time']
    return latest_checkin >= threshold


def ids_in_group(group_label, active_only=True):
    query = {"group": group_label}
    projection = {"checkins": 1}
    cursor = db.installs.find(query, projection)
    return [r['_id'] for r in cursor if not active_only or is_active(r)]


if args.active:
    num_active = 0
    num_inactive = 0

    for row in db.installs.find({}, {"checkins": 1}):
        if is_active(row):
            num_active += 1
        else:
            num_inactive += 1

    print "# Active:   {}".format(num_active)
    print "# Inactive: {}".format(num_inactive)

if args.inemails:
    for row in db.emails.find({}, {"checkins": 1}):
        if is_active(row):
            print row["_id"]

if args.outemails:
    for row in db.emails.find({}, {"checkins": 1}):
        if not is_active(row):
            print row["_id"]

if args.passwords:
    projection = {"checkins": 1, "pws": 1}
    query = {}
    if args.group:
        query['group'] = args.group
    cursor = db.installs.find(query, projection)
    # If we care about all passwords logged, irregardless of domain,
    # then we just need a simple sum (simple case)
    if not args.domains:
        print sum([len(row["pws"]) for row in cursor if is_active(row)])
    else:
        watched_domains = watched_domains()
        count = 0
        pwd_iterator = (row['pws'] for row in cursor if is_active(row))
        print sum([1 for r in pwd_iterator if r['domain'] in watched_domain])

if args.group and not args.passwords:
    print "\n".join(ids_in_group(args.group))

if args.misses and args.hits:
    raise Exception("Cannot ask for hits and misses at the same time.")

if args.misses or args.hits:
    for row in db.emails.find({}):
        if "checkins" not in row or len(row["checkins"]) < 2:
            print row["_id"]
            continue
        prev_time = None
        adjoining_dates = []
        for checkin in row["checkins"]:
            time = checkin['time']
            if prev_time:
                adjoining_dates.append((prev_time, time))
            prev_time = time

        max_time = max([b - a for a, b in adjoining_dates])

        if args.misses and max_time > threshold_diff:
            print row["_id"]

        if args.hits and max_time <= threshold_diff and is_active(row):
            print row["_id"]
