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
    return MONGO['client'].installs


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
                      "client": client_name, "checkins": [], "pws": []}
            db().insert(record, callback=self._on_record)

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
        ext_version = self.get_argument("ext_version", False)
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
                "checkins": {"created_on": datetime.now(), "ext_version": ext_version}
            }}
            db().update(query, update, callback=cb)

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
            query = {"_id": install_id}
            update = {"$push": {
                "pws": {"host": host, "created_on": datetime.now()}
            }}
            db().update(query, update, callback=self._on_record)

    def _on_record(self, result, error):
        if error:
            app_log.debug("Error recording password: {error}".format(error=error))
        self.finish()
