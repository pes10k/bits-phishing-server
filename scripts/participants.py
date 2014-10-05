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
parser.add_argument("--active", "-a", action="store_true",
                    help="Prints statistics about how many plugins are " +
                         "currently active. A plugin is considered active " +
                         "if it has checked in during the last 48 hours.")
args = parser.parse_args()

script_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
config = imp.load_source('config', os.path.join(root_dir, 'config.py'))

m = config.mongo
connection = pymongo.MongoClient(m['host'], m['port'])
db = connection[m['dbname']]

if args.active:
    threshold = datetime.datetime.now() - datetime.timedelta(days=2)

    num_active = 0
    num_inactive = 1

    for row in db.installs.find({}, {"checkins": 1}):
        checkins = row["checkins"]
        if len(checkins) == 0:
            num_inactive += 1
            continue

        latest_checkin = checkins[-1]['time']
        if latest_checkin >= threshold:
            num_active += 1
        else:
            num_inactive += 1

    print "# Active:   {}".format(num_active)
    print "# Inactive: {}".format(num_inactive)
    sys.exit()
