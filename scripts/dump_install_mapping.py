#!/usr/bin/env python
import common

m = common.mongo()
installs = m['installs']
for row in installs.find({}, {"_id": 1, "group": 1}):
    print row['_id'], row['group']
