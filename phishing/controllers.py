import os
import config
import tornado.web
import uuid
import tornado.gen
from tornado.log import app_log
from tornado.escape import json_encode, json_decode
from datetime import datetime

# Modules only used when debugging
import time
import math

MONGO = {'client': None}
COOKIE_RULES_PATH = os.path.join(config.root_dir, "files", "cookie-rules.json")

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

    def _error_out(self, error):
        app_log.error(u"{0}: {1}".format(type(self).__name__, error))
        self.write(json_encode({"ok": False, "msg": error}))
        self.finish()

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
                "usage": [],
                "autofills": []
            }
            db = self.settings['db']
            response = {}

            try:
                yield db.installs.insert(record)
                is_error = False
            except Exception, e:
                is_error = True
                app_log.info("Error writing registration: {error}".format(error=str(e)))
                response['msg'] = "ID already registered"

            response['ok'] = not is_error

            if not is_error:
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

            db = self.settings['db']
            try:
                yield db.installs.update(query, update)
            except Exception, e:
                self._error_out(u"Error writing checkin: {0}".format(str(e)))

            self._ok_out({"msg": json_decode(rules), "active": config.active})


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

            db = self.settings['db']
            try:
                yield db.installs.update(query, update)
            except Exception, e:
                self._error_out(u"Error writing autofill: {0}".format(str(e)))
            self._ok_out()

class PasswordEntered(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
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
            db = self.settings['db']
            try:
                yield db.installs.update(query, update)
            except Exception, e:
                self._error_out("Error recording password: {error}".format(error=str(e)))
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
            db = self.settings['db']
            for histogram in histograms:
                update = {"$push": {"usage": histogram}}
                try:
                    db.installs.update(query, update)
                except Exception, e:
                    self._error_out(u"Error attempting to append histogram data: {0}".format(str(e)))
                    return
            self._ok_out()


class EmailUpdate(PhishingRequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        email = self.get_argument('email', False)
        error_msg = None

        db = self.settings['db']

        if not email:
            error_msg = "Missing email to update"

        if not error_msg:
            query = {"_id": email}
            try:
                msg = yield db.emails.find_one(query)
            except Exception, e:
                error_msg = str(e)

        if not error_msg and not msg:
            record = {"_id": email, "checkins": []}
            try:
                yield db.emails.insert(record)
            except Exception, e:
                error_msg = str(e)

        if not error_msg:
            update_query = {"_id": email}
            update_data = {"$push": {"checkins": datetime.now()}}
            try:
                yield db.emails.update(update_query, update_data)
            except Exception, e:
                error_msg = str(e)

        if error_msg:
            self._error_out("Error recording password: {error}".format(error=error_msg))
        else:
            self._ok_out({"error": error_msg})


class CookieSetTest(PhishingRequestHandler):
    """Simple test class that sets two cookies, `test_long` and `test_short`
    on the requester.  This controller is only accessible when the server is
    in debug mode.

    Both cookies will have the same expiration time, but the
    other end of the test, the browser plugin, will set the short one
    to have a shorter expiration time.
    """

    def get(self):
        # Set the expiration date by default to be 1 year from now
        expiraton_time = math.floor(time.time()) + 31536000
        self.set_cookie('test_short', 'short_value', expires=expiraton_time)
        self.set_cookie('test_long', 'short_long', expires=expiraton_time)
        self.write("Successfully wrote two test cookies.")
        self.finish()
