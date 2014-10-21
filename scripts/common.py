"""Common tools useful for normalizing the environment so that we
can call scripts in the ./scripts directory, but still utilize code
and modules elsewhere in the repo."""

import os.path
import imp
import pymongo

script_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
config = imp.load_source('config', os.path.join(root_dir, 'config.py'))

def mongo():
    m = config.mongo_params
    connection = pymongo.MongoClient(m['host'], m['port'])
    db = connection[config.mongo_database]
    return db
