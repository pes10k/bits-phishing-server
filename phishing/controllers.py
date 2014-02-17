import os
import config
import tornado.web
import asyncmongo
import uuid
import tornado.gen
from tornado.log import app_log
from tornado.escape import json_encode, json_decode
from datetime import datetime

MONGO = {'client': None}
COOKIE_RULES_PATH = os.path.join(config.root_dir, "files", "cookie-rules.json")

def db(collection="installs"):
    if not MONGO['client']:
        MONGO['client'] = asyncmongo.Client(**config.mongo)
    return MONGO['client'][collection]

def assign_group():
    next_group = None
    if not assign_group._last_group or assign_group._last_group == "control":
        next_group = "reauth"
    elif assign_group._last_group == "reauth":
        next_group = "autofill"
    else:
        next_group = "control"
    assign_group._last_group = next_group
    return next_group
assign_group._last_group = None

class PhishingRequestHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def _error_out(self, error):
        app_log.error(u"{0}: {1}".format(type(self).__name__, error))
        self.write(json_encode({"ok": False, "msg": error}))
        self.finish()

    @tornado.web.asynchronous
    def _ok_out(self, params=None):
        if not params:
            params = {}
        params["ok"] = True
        self.write(json_encode(params))
        self.finish()


class Register(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        browser = self.get_argument("browser", False)
        version = self.get_argument("version", False)
        debug = self.get_argument("debug", False)

        if not version:
            self._error_out("missing extension version");
        elif not browser:
            self._error_out("missing browser name")
        else:
            record = {
                "_id": uuid.uuid4().hex,
                "group": assign_group(),
                "created_on": datetime.now(),
                "browser": browser,
                "version": version,
                "debug": debug,
                "checkins": [],
                "pws": [],
                "reauths": [],
                "usage": [],
                "autofills": []
            }
            result, error_rs = yield tornado.gen.Task(db().insert, record)
            response = {"ok": not error_rs['error']}
            if error_rs['error']:
                app_log.info("Error writing registration: {error}".format(error=error_rs['error']))
                response['msg'] = "ID already registered"
            else:
                response['msg'] = "registered"
                response['group'] = record['group']
                response['_id'] = record['_id']
                response['created_on'] = record['created_on'].isoformat()
            self.write(json_encode(response))
            self.finish()


class CookieRules(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        install_id = self.get_argument("id", False)
        if not install_id:
            self._error_out("missing install id")
        else:
            handle = open(COOKIE_RULES_PATH, 'r')
            rules = handle.read()
            handle.close()
            query = {"_id": install_id}
            update = {"$push": {"checkins": datetime.now()}}
            update_result, error = yield tornado.gen.Task(db().update, query, update)
            if error['error']:
                self._error_out(u"Error writing checkin: {0}".format(error['error']))
            else:
                self._ok_out({"msg": json_decode(rules), "active": config.active})

class Reauth(PhishingRequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        domain = self.get_argument("domain", False)
        if not install_id:
            self._error_out("missing install id")
        elif not domain:
            self._error_out("missing domain")
        else:
            query = {"_id": install_id}
            update = {"$push": {
                "reauths": {
                    "date": datetime.now(),
                    "domain": domain
               }
            }}
            db().update(query, update, callback=self._on_record)

    def _on_record(self, result, error):
        if error:
            self._error_out("Error recording password: {error}".format(error=error))
        else:
            self._ok_out()


class PasswordAutofill(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        install_id = self.get_argument("id", False)
        domain = self.get_argument("domain", False)
        url = self.get_argument("url", False)
        if not install_id:
            self._error_out("missing install id")
        elif not domain:
            self._error_out("missing domain")
        elif not url:
            self._error_out("missing url")
        else:
            query = {"_id": install_id}
            update = {"$push": {
                "autofills": {
                    "date": datetime.now(),
                    "domain": domain,
                    "url": url
               }
            }}
            update_result, error = yield tornado.gen.Task(db().update, query, update)
            if error['error']:
                self._error_out(u"Error writing autofill: {0}".format(error['error']))
            else:
                self._ok_out()


class PasswordEntered(PhishingRequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        domain = self.get_argument("domain", False)
        url = self.get_argument("url", False)
        pw_hash = self.get_argument("pw_hash", False)
        pw_strength = self.get_argument("pw_strength", False)

        if not install_id:
            self._error_out("missing install id")
        elif not pw_hash:
            self._error_out("missing password hash")
        elif not pw_strength:
            self._error_out("missing password strength")
        else:
            query = {"_id": install_id}
            update = {"$push": {
                "pws": {
                    "date": datetime.now(),
                    "domain": domain,
                    "url": url,
                    "hash": pw_hash,
                    "strength": pw_strength
               }
            }}
            db().update(query, update, callback=self._on_record)

    def _on_record(self, result, error):
        if error:
            self._error_out("Error recording password: {error}".format(error=error))
        else:
            self._ok_out()

class BrowsingCounts(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        install_id = self.get_argument("id", False)
        histograms = self.get_argument("histograms", False)
        app_log.info(u"histograms: " + str(histograms))
        if not install_id:
            self._error_out("missing install id")
        elif not histograms:
            self._error_out("missing usage histograms")
        else:
            histograms = json_decode(histograms)
            query = {"_id": install_id}
            for histogram in histograms:
                update = {"$push": {"usage": histogram}}
                update_result, error = yield tornado.gen.Task(db().update, query, update)
                if error['error']:
                    self._error_out(u"Error attempting to append histogram data: {0}".format(error['error']))
                    break
            if not error['error']:
                self._ok_out()


class EmailUpdate(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        email = self.get_argument('email', False)
        error_msg = None

        if not email:
            error_msg = "Missing email to update"

        if not error_msg:
            query = {"_id": email}
            find_result, error = yield tornado.gen.Task(db('emails').find, query)
            error_msg = error['error']

        if not error_msg and not find_result[0]:
            record = {"_id": email, "checkins": []}
            insert_result, error = yield tornado.gen.Task(db('emails').insert, record)
            error_msg = error['error']

        if not error_msg:
            update_query = {"_id": email}
            update_data = {"$push": {"checkins": datetime.now()}}
            update_result, error = yield tornado.gen.Task(db('emails').update, update_query, update_data)
            error_msg = error['error']

        if error_msg:
            self._error_out("Error recording password: {error}".format(error=error_msg))
        else:
            self._ok_out({"error": error_msg})
