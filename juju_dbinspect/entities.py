#!/usr/bin/env python
"""
license: GPLv3
author: kapil.foss at gmail dot com
"""
import itertools
from bson.objectid import ObjectId


OMIT = {'txn-queue': 0, 'txn-revno': 0}


def empty_err(v, k):
    if v is None:
        raise ValueError("No entity found for %s" % k)
    return v


def omit(*keys):
    d = dict(OMIT)
    d.update(dict(zip(keys, itertools.repeat(0))))
    return d


shell_commands = []


def shellfunc(f):
    """Register a function to be available in the dbshell"""
    shell_commands.append(f)
    return f


@shellfunc
def units(db):
    """Get the names of all units in the environment."""
    return [i['_id'] for i in db.units.find({}, {'_id': 1})]


@shellfunc
def unit(db, uid):
    """Get a unit by name."""
    u = empty_err(
        db.units.find_one(
            {"_id": uid}, omit('nonce', 'passwordhash'), as_class=Unit),
        uid)
    u.db = db
    return u


@shellfunc
def services(db):
    """Get the names of all services in the environment."""
    return [i['_id'] for i in db.services.find({}, {'_id': 1})]


@shellfunc
def service(db, sid):
    """Get a service by name."""
    s = empty_err(
        db.services.find_one({"_id": sid}, OMIT, as_class=Service),
        sid)
    s.db = db
    return s


@shellfunc
def machines(db):
    """Get the ids of all machines in the environment."""
    return [i['_id'] for i in db.machines.find({}, {'_id': 1})]


@shellfunc
def machine(db, mid):
    """Get a machine by id."""
    m = db.machines.find_one(
        {"_id": mid}, omit('nonce', 'passwordhash'), as_class=Machine)
    m.db = db
    return m


@shellfunc
def relations(db, service=None):
    """Get all the relations in the environment."""
    rels = [i['_id'] for i in db.relations.find({}, {'_id': 1})]
    if not service:
        return rels
    else:
        return [r for r in rels if "%s:" % service in r]


@shellfunc
def relation(db, relation_ep):
    """Get the relation from the given endpoint(s).
    """
    m = empty_err(
        db.relations.find_one({"_id": relation_ep}, OMIT, as_class=Relation),
        relation_ep)
    m.db = db
    return m


@shellfunc
def charms(db):
    """Get all the charms in the environment."""
    return [i['_id'] for i in db.charms.find({}, {'_id': 1})]


@shellfunc
def charm(db, charm_url):
    """Get a charm by url."""
    c = empty_err(
        db.charms.find_one({"_id": charm_url}, OMIT, as_class=Charm),
        charm_url)
    c.db = db
    return c


@shellfunc
def history(db, count=100):
    """Retrieve last n transactions on the environment."""
    size = db.txns.count()
    for t in db.txns.find(skip=(size-count)):
        Txn.format(t)


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

    @property
    def formatted(self):
        d = dict(self)
        d['constraints'] = self.constraints
        d['status'] = self.status
        return d


class RelationEndpoint(Entity):
    __slots__ = ()

    @property
    def charm_url(self):
        return self['charmurl']

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
    elif ep['relation']['role'] == 'requirer':
        return 'provider'
    return 'peer'


class Unit(RelationEndpoint):
    __slots__ = ('db',)

    ref_letter = "u"

    @property
    def service(self):
        return service(self.db, self['service'])

    def relation_data(self, spec):
        found = False
        for r in self.relations:
            for ep in r['endpoints']:
                if ep['servicename'] == spec:
                    found = r, _invert_role(ep)
                    break
            if found:
                break
        if not found:
            return None
        r, self_role = found
        u_rid = "r#%s#%s#%s" % (r['id'], self_role, self.id)
        return self.db.settings.find_one({"_id": u_rid}, omit("_id"))


class Service(RelationEndpoint):
    __slots__ = ('db',)

    ref_letter = "s"

    @property
    def config(self):
        conf_key = "%s#%s#%s" % (
            self.ref_letter,
            self.id,
            self.charm_url)
        return self.db.settings.find_one(
            {"_id": conf_key}, omit("_id"))

    @property
    def units(self):
        units = []
        for u in self.db.units.find(
                {"service": self.id}, omit('nonce', 'passwordhash'),
                as_class=Unit):
            u.db = self.db
            units.append(u)
        return units

    @property
    def formatted(self):
        d = super(Service, self).formatted
        d['config'] = self.config
        return d


class Relation(Base):

    @property
    def unit_ids(self):
        return [u.rsplit('#', 1)[1] for u in self._unit_rel_ids()]

    def _unit_rel_ids(self):
        r_id = 'r#%d#' % self['id']
        # This can be fulfilled from index, but a prefix begin/end
        # would be faster.
        return [u['_id'] for u in self.db.settings.find(
            {'_id': {'$regex': '^%s.*' % r_id}}, {"_id": 1})]

    def history(self):
        # Won't include deleted units, would need to iterate
        # full set of units based on svc seq.
        q = self.db.txns.find(
            {"o.c": "settings", 'o.d': {'$in': self._unit_rel_ids()}})
        for t in q:
            Txn.format(t)


class Machine(Entity):
    __slots__ = ('db',)

    ref_letter = "m"

    @property
    def units(self):
        units = []
        for unit in self.db.units.find(
                {'machineid': self.id}, OMIT, as_class=Unit):
            unit.db = self.db
            units.append(unit)
        return units

    @property
    def formatted(self):
        d = super(Machine, self).formatted
        d['units'] = [u['_id'] for u in self.units]
        return d


class Charm(Entity):
    __slots__ = ('db',)

    @property
    def config(self):
        return self['config']

    @property
    def services(self):
        services = []
        for svc in self.db.services.find(
                {'charmurl': self.id}, OMIT, as_class=Service):
            svc.db = self.db
            services.append(svc)
        return services


class Txn(dict):
    __slots__ = ()

    state_labels = {
        1: 'preparing',
        2: 'prepared',
        3: 'aborting',
        4: 'applying',
        5: 'aborted',
        6: 'applied'}

    @classmethod
    def format(cls, txn):
        print ObjectId(txn['_id']).generation_time.strftime(
            '%Y/%m/%d-%H:%M:%S'), cls.state_labels[txn['s']]
        for o in txn['o']:
            print "    %s:%s" % (o['c'], o['d']),
            if 1:
                if 'i' in o:
                    print "create", o['i']
                elif 'u' in o:
                    print "update", o['u']
                elif 'a' in o:
                    print "cond", o['a']
                elif 'r' in o:
                    print "remove"
                else:
                    raise AssertionError(
                        "Invalid Transaction Operation %s" % o)
