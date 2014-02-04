import os
import config
import tornado.web
import asyncmongo
import uuid
import tornado.gen
import random
from tornado.log import app_log
from tornado.escape import json_encode, json_decode
from datetime import datetime

MONGO = {'client': None}
COOKIE_RULES_PATH = os.path.join(config.root_dir, "files", "cookie-rules.json")

def db(collection="installs"):
    if not MONGO['client']:
        MONGO['client'] = asyncmongo.Client(**config.mongo)
    return MONGO['client'][collection]


class Register(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        browser = self.get_argument("browser", False)
        version = self.get_argument("version", False)
        debug = self.get_argument("debug", False)

        if not version:
            self.write(json_encode({"ok": False, "msg": "missing extension version"}))
            self.finish()
        elif not browser:
            self.write(json_encode({"ok": False, "msg": "missing browser name"}))
            self.finish()
        else:
            record = {
                "_id": uuid.uuid4().hex,
                "group": "experiment" if random.choice((True, False)) else "control",
                "created_on": datetime.now(),
                "browser": browser,
                "version": version,
                "debug": debug,
                "checkins": [],
                "pws": []
            }
            result, error_rs = yield tornado.gen.Task(db().insert, record)
            response = {"ok": not error_rs['error']}
            if error_rs['error']:
                app_log.debug("Error writing registration: {error}".format(error=error_rs['error']))
                response['msg'] = "ID already registered"
            else:
                response['msg'] = "registered"
                response['group'] = record['group']
                response['_id'] = record['_id']
                response['created_on'] = record['created_on'].isoformat()
            self.write(json_encode(response))
            self.finish()


class CookieRules(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        if not install_id:
            self.write(json_encode({"ok": False, "msg": "missing install id"}))
            self.finish()
        else:
            handle = open(COOKIE_RULES_PATH, 'r')
            rules = handle.read()
            handle.close()
            cb = lambda result, error: self._on_record(rules, result, error)
            query = {"_id": install_id}
            update = {"$push": {
                "checkins": datetime.now()
            }}
            db().update(query, update, callback=cb)

    # First record the checkin, then read the latest cookie list and send
    # it back over the wire
    def _on_record(self, rules, result, error):
        if error:
            app_log.debug("Error writing checkin: {error}".format(error=error))
            rs = {"ok": False, "msg": error}
        else:
            rs = {"ok": True, "msg": json_decode(rules), "active": config.active}
        self.write(json_encode(rs))
        self.finish()

class PasswordEntered(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        if not install_id:
            error = "missing install id"
            self.write(json_encode({"ok": False, "msg": error}))
            self.finish()
        else:
            query = {"_id": install_id}
            update = {"$push": {
                "pws": datetime.now()
            }}
            db().update(query, update, callback=self._on_record)

    def _on_record(self, result, error):
        if error:
            app_log.debug("Error recording password: {error}".format(error=error))
        self.write(json_encode({"ok": True}))
        self.finish()

class EmailUpdate(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        email = self.get_argument('email', False)
        error_msg = None

        if not email:
            error_msg = "Missing email to update"

        if not error_msg:
            query = {
                "_id": email
            }
            find_result, error = yield tornado.gen.Task(db('emails').find, query)
            error_msg = error['error']

        if not error_msg and not find_result[0]:
            record = {
                "_id": email,
                "checkins": []
            }
            insert_result, error = yield tornado.gen.Task(db('emails').insert, record)
            error_msg = error['error']

        if not error_msg:
            update_query = {
                "_id": email
            }
            update_data = {
                "$push": {
                    "checkins": datetime.now()
                }
            }
            update_result, error = yield tornado.gen.Task(db('emails').update, update_query, update_data)
            error_msg = error['error']

        if error_msg:
            app_log.debug("Error recording password: {error}".format(error=error_msg))

        self.write(json_encode({
            "ok": not error_msg,
            "error": error_msg
        }))
        self.finish()
