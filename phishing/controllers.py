import os
import config
import tornado.web
import asyncmongo
from tornado.log import app_log
from tornado.escape import json_encode, json_decode
from datetime import datetime

MONGO = {'client': None}
COOKIE_RULES_PATH = os.path.join(config.root_dir, "files", "cookie-rules.json")

def db():
    if not MONGO['client']:
        MONGO['client'] = asyncmongo.Client(**config.mongo)
    return MONGO['client']


class Register(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        ext_version = self.get_argument("ext_version", False)
        client_name = self.get_argument("client", False)
        if not install_id:
            self.write(json_encode({"ok": False, "msg": "missing install id"}))
            self.finish()
        elif not ext_version:
            self.write(json_encode({"ok": False, "msg": "missing extension version"}))
            self.finish()
        elif not client_name:
            self.write(json_encode({"ok": False, "msg": "missing client name"}))
            self.finish()
        else:
            record = {"_id": install_id, "created_on": datetime.now(),
                      "extension_version": ext_version, "client": client_name}
            db().registrations.insert(record, callback=self._on_record)

    def _on_record(self, result, error):
        response = {"ok": not error}
        if error:
            app_log.debug("Error writing registration: {error}".format(error=error))
            response['msg'] = "ID already registered"
        else:
            response['msg'] = "registered"
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
            record = {"install_id": install_id, "created_on": datetime.now()}
            db().checkins.insert(record, callback=cb)

    # First record the checkin, then read the latest cookie list and send
    # it back over the wire
    def _on_record(self, rules, result, error):
        if error:
            app_log.debug("Error writing checkin: {error}".format(error=error))
            rs = {"ok": False, "msg": error}
        else:
            rs = {"ok": True, "msg": json_decode(rules)}
        self.write(json_encode(rs))
        self.finish()

class PasswordEntered(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        install_id = self.get_argument("id", False)
        host = self.get_argument("host", False)
        if not install_id or not host:
            error = "missing install id '{0}'' or host '{1}'".format(install_id, host)
            self.write(json_encode({"ok": False, "msg": error}))
            self.finish()
        else:
            record = {"install_id": install_id, "host": host, "created_on": datetime.now()}
            db().password_entries.insert(record, callback=self._on_record)

    def _on_record(self, result, error):
        if error:
            app_log.debug("Error recording password: {error}".format(error=error))
        self.finish()
