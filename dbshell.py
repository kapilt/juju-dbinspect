#!/usr/bin/env python
"""
Use at own risk.


kapil@realms-slice:~$ python dbshell.py fargo
Juju DB Shell

####
# The basics

>>> units()
[u'message/0', u'db/0', u'identity/0', u'meter/0']
>>> machines()
[u'0', u'230', u'232', u'233', u'231']
>>> services()
[u'db', u'identity', u'message', u'meter']

####
# Let's inspect machine 0's constraints

>> machine('0').constraints
  {u'cpupower': None, u'container': None, u'cpucores': None,
   u'mem': None, u'arch': None, u'rootdisk': None}

####
# Let's inspect the relation data between identity
# and metering service units.

>>> unit('meter/0').relation_data('identity')
 {u'_id': u'r#190#requirer#meter/0',
  u'admin_url': u'http://10.0.3.103:8777',
  u'internal_url': u'http://10.0.3.103:8777',
  u'private-address': u'10.0.3.103',
  u'public_url': u'http://10.0.3.103:8777',
  u'region': u'RegionOne',
  u'requested_roles': u'ResellerAdmin',
  u'service': u'ceilometer'}

>>> unit('identity/0').relation_data('meter')
 {u'_id': u'r#190#provider#identity/0',
  u'admin_token': u'witieweithoinaiwuojeFiepuneiseye',
  u'auth_host': u'10.0.3.27',
  u'auth_port': u'35357',
  u'auth_protocol': u'https',
  u'ca_cert': u'omitted for brevity',
  u'https_keystone': u'True',
  u'private-address': u'10.0.3.27',
  u'service_host': u'10.0.3.27',
  u'service_password': u'eingahVeehivaiHahnohngahTooYizei',
  u'service_port': u'5000',
  u'service_protocol': u'https',
  u'service_tenant': u'services',
  u'service_username': u'ceilometer',
  u'ssl_cert': u'omitted for brevity',
  u'ssl_key': u'omitted for brevity'}
>>>

author: kapil.foss at gmail dot com
"""
import code
import functools
import itertools
import os
from pprint import pprint
import tempfile
import subprocess
import sys
import yaml

from pymongo import MongoClient

OMIT = {'txn-queue': 0, 'txn-revno': 0}


def omit(*keys):
    d = dict(OMIT)
    d.update(dict(zip(keys, itertools.repeat(0))))
    return d


def units(db):
    return [i['_id'] for i in db.units.find({}, {'_id': 1})]


def unit(db, uid):
    u = db.units.find_one(
        {"_id": uid}, omit('nonce', 'passwordhash'), as_class=Unit)
    u.db = db
    return u


def services(db):
    return [i['_id'] for i in db.services.find({}, {'_id': 1})]


def service(db, sid):
    s = db.services.find_one({"_id": sid}, OMIT, as_class=Service)
    s.db = db
    return s


def machines(db):
    return [i['_id'] for i in db.machines.find({}, {'_id': 1})]


def machine(db, mid):
    m = db.machines.find_one(
        {"_id": mid}, omit('nonce', 'passwordhash'), as_class=Machine)
    m.db = db
    return m


def relations(db, service=None):
    rels = [i['_id'] for i in db.relations.find({}, {'_id': 1})]
    if not service:
        return rels
    else:
        return [r for r in rels if "%s:" % service in r]


def relation(db, unit, target_service):
    pass


commands = [
    units, unit, services, service,
    machines, machine, relations]


class Base(dict):
    __slots__ = ()
    db = None

    @property
    def id(self):
        return self['_id']


class Entity(Base):
    __slots__ = ()

    @property
    def constraints(self):
        return self.db.constraints.find_one(
            {"_id": "%s#%s" % (self.ref_letter, self.id)}, omit('_id'))

    @property
    def status(self):
        return self.db.statuses.find_one(
            {"_id": "%s#%s" % (self.ref_letter, self.id)}, omit('_id'))


class RelationEndpoint(Entity):
    __slots__ = ()

    @property
    def service_name(self):
        return self.id.split("/", 1)[0]

    @property
    def relations(self):
        rels = self.db.relations.find(
            {'endpoints': {'$elemMatch': {
                'servicename': self.service_name}}},
            OMIT)
        return list(rels)

    @property
    def related_services(self):
        related = []
        for r in self.relations:
            if len(r['endpoints']) == 1:
                continue
            for ep in r['endpoints']:
                if ep['servicename'] != self.service_name:
                    related.append(service(self.db, ep['servicename']))
        return related


def _invert_role(ep):
    if ep['relation']['role'] == 'provider':
        return 'requirer'
    return 'provider'


class Unit(RelationEndpoint):
    __slots__ = ('db',)

    ref_letter = "u"

    @property
    def charm(self):
        return self['charmurl']

    def relation_data(self, spec):
        found = False
        for r in self.relations:
            for ep in r['endpoints']:
                if ep['servicename'] == spec:
                    found = r, _invert_role(ep)
                    break
        if not found:
            return None
        r, self_role = found
        u_rid = "r#%s#%s#%s" % (
            r['id'], self_role, self.id)
        return self.db.settings.find_one(
            {"_id": u_rid}, OMIT)


class Service(RelationEndpoint):
    __slots__ = ('db',)

    ref_letter = "s"

    @property
    def charm(self):
        return self['charmurl']


class Machine(Entity):
    __slots__ = ('db',)

    ref_letter = "m"


def main(env_name):

    conf_path = os.path.join(
        os.path.expanduser(
            os.environ.get("JUJU_HOME", "~/.juju")),
        "environments",
        "%s.jenv" % env_name)

    with open(conf_path) as fh:
        data = yaml.safe_load(fh.read())
        env_data = data.get('bootstrap-config', {})

        # if 1.17/1.18 do one set of hacks to work around juju
        if 'bootstrap-host' in env_data:
            # db password only stored in old-password of agent.conf
            # http://pad.lv/1270434  marked won't fix/opinion
            output = subprocess.check_output([
                "juju", "run", "-e", env_name, "--machine", "0",
                "sudo cat /var/lib/juju/agents/machine-0/agent.conf"])
            mdata = yaml.safe_load(output)
            env_data['admin-secret'] = mdata['oldpassword']

        # if 1.16 do another
        else:
            output = subprocess.check_output(
                ["juju", "api-endpoints", "-e", env_name])
            host, port = output.strip().split(":", 1)
            env_data['bootstrap-host'] = host

        uri = ("mongodb://"
               "%(bootstrap-host)s:%(state-port)s"
               "/juju?w=1&ssl=true") % env_data

    with tempfile.NamedTemporaryFile() as fh:
        password = env_data['admin-secret']
        client = MongoClient(uri)
        client.admin.authenticate('admin', password)
        db = client.juju

        ctxt = {'client': client, 'db': db}
        for f in commands:
            bound = functools.partial(f, db)
            bound.__name__ = f.__name__
            ctxt[f.__name__] = bound
        ctxt['pprint'] = pprint
        code.interact(local=ctxt, banner="Juju DB Shell")


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except:
       import pdb, traceback, sys
       traceback.print_exc()
       pdb.post_mortem(sys.exc_info()[-1])
