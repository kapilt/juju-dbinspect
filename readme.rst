Juju DB Introspection
---------------------

Provide introspection tools to understand the state of the system,
including relation data which is normally opaque.

***Use at own risk.***

***This can break between any juju version***

This is very specific to the underlying database structures of any
given juju version, which is an implementation detail subject to
change without notice.

*** Do no write to the db ***

Do not attempt to write to any of these structures, bad things will
happen and you get to keep all the broken things. Use the juju api if
you need to modify something. Juju uses a client-side transaction
library that does multi-document mods atomically and is dependent on
all writers using the same txn library. More details on that here for
the curious

http://blog.labix.org/2012/08/22/multi-doc-transactions-for-mongodb


Install
-------

TODO

Depending on your provider you may need to open up access to port 37017 on
the state server (machine 0 if not ha).


Intro
-----


Usage::

  kapil@realms-slice:~$ python dbshell.py syracuse
  Juju DB Shell
  >>>

The basics::

  >>> units()
  [u'message/0', u'db/0', u'identity/0', u'meter/0']
  >>> machines()
  [u'0', u'230', u'232', u'233', u'231']
  >>> services()
  [u'db', u'identity', u'message', u'meter']
  >>> pprint(relations())
  [u'db:cluster',
   u'message:cluster',
   u'identity:cluster',
   u'meter:identity-service identity:identity-service',
   u'identity:shared-db db:shared-db',
   u'meter:amqp message:amqp']

Let's inspect machine 0's constraints::

  >> machine('0').constraints
    {u'cpupower': None, u'container': None, u'cpucores': None,
     u'mem': None, u'arch': None, u'rootdisk': None}

And what's going on with the meter/0 unit::
  
   >>> pprint(unit('meter/0'))

   {u'_id': u'meter/0',
    u'charmurl': u'local:precise/ceilometer-52',
    u'life': 0,
    u'machineid': u'233',
    u'ports': [{u'number': 8777, u'protocol': u'tcp'}],
    u'principal': u'',
    u'privateaddress': u'10.0.3.103',
    u'publicaddress': u'10.0.3.103',
    u'resolved': u'',
    u'series': u'precise',
    u'service': u'meter',
    u'subordinates': [],
    u'tools': {u'sha256': u'',
               u'size': 0L,
               u'url': u'',
               u'version': u'1.17.3.1-precise-amd64'}}


    >>> unit('meter/0').status
    {u'status': u'started', u'statusinfo': u'', u'statusdata': {}}

Let's inspect the relation data between identity
and metering service units::

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

Available helper commands

    - units
    - unit
    - services
    - service
    - machines
    - machine
    - relations
    - charms


