#!/usr/bin/python
"""
CLI for interacting with the MongoDB instance that stores current plugin
instance.  More useful information / options are available with --help
"""

import datetime
import imp
import os
import sys
import pymongo
import argparse

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
                    help="If provided, lists all install ids that are active " +
                         "and assigned to a given group.")
args = parser.parse_args()


script_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
config = imp.load_source('config', os.path.join(root_dir, 'config.py'))

m = config.mongo_params
connection = pymongo.MongoClient(m['host'], m['port'])
db = connection[config.mongo_database]

threshold = datetime.datetime.now() - datetime.timedelta(days=args.days)

def is_active(row):
    checkins = row["checkins"]
    if len(checkins) == 0:
        return False
    latest_checkin = checkins[-1]['time']
    return latest_checkin >= threshold

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

if args.group:
    for row in db.installs.find({"group": args.group}, {"checkins": 1}):
        if is_active(row):
            print row["_id"]