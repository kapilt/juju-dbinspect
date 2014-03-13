Juju DB Introspection
---------------------

Provide introspection tools to understand the state of the system,
including relation data which is normally opaque.

This is intended as a foresnic tool for advanced users to diagnose
or examine the state of the environment.

***Use at own risk. This can break between any juju versions***

This is very specific to the underlying database structures of any
given juju version, which is an implementation detail subject to
change without notice.

That said the implementation here works across all extant releases of
juju core. However past success is no guarantee of future compatiblity.

*** Do no write to the db ***

Do not attempt to write to any of these structures, bad things will
happen and you get to keep all the broken things. Use the juju api if
you need to modify something. Juju uses a mongodb client-side transaction
library that does multi-document mods atomically and is dependent on
all writers using the same txn library. More details on that here for
the curious

http://blog.labix.org/2012/08/22/multi-doc-transactions-for-mongodb


Install
=======

Available via pypi, dependencies are pymongo and pyyaml::

  $ pip install juju-dbinspect

Depending on your provider and juju version you may need to open up
access to port 37017 on the state server (machine 0 if not ha).


CLI Intro
=========


CLI Usage is documented via the built-in help::

  $ juju db --help

  juju db --help
  usage: juju-db [-h] [-e ENVIRONMENT] [-v] targets [targets ...]

  Juju database introspection

    Drop into an interactive python shell.
      $ juju db shell

    Get the last n transactions (default 100) that have modified the
    environment.
      $ juju db history [n]

    Get the names of all the services in the system.
      $ juju db services

    Get the names of all the units in the system.
      $ juju db units

    Get the details on machine 0.
      $ juju db 0

    Get the details on the unit mysql/0.
      $ juju db mysql/0

    Get the details on the mysql service::
      $ juju db mysql

    Get the relation settings for the mysql/0 unit in the wordpress relation::
      $ juju db mysql/0 wordpress


  positional arguments:
    targets

  optional arguments:
    -h, --help            show this help message and exit
    -e ENVIRONMENT, --environment ENVIRONMENT
                        Juju environment to operate on
    -v, --verbose         Verbose output



DB Interactive Shell
====================

Also available with the same core functionality is a python interactive shell with access to the
db. The shell can be started with::

  kapil@realms-slice:~$ juju db shell -e syracuse
  Juju DB Shell
  >>>

Basics entity iteration commands::

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

What units are on machine 230::

  >> machine('230').units


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

Let's inspect the identity to metering service relation and look at the relation data
of their units::

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


We can also examine the history of the environment via introspection of the transaction log::

  >>> history()

  2014/03/06-19:31:39 applied
    units:message/0 update {u'$set': {u'privateaddress': u'10.0.3.215'}}
  2014/03/06-19:31:39 applied
    units:message/0 update {u'$set': {u'publicaddress': u'10.0.3.215'}}
  2014/03/06-19:31:40 applied
    settingsrefs:s#message#local:precise/rabbitmq-server-146 update {u'$inc': {u'refcount': 1}}
    units:message/0 update {u'$set': {u'charmurl': u'local:precise/rabbitmq-server-146'}}
  2014/03/06-19:33:07 applied
    units:message/0 update {u'$addToSet': {u'ports': {u'protocol': u'tcp', u'number': 5672}}}
  2014/03/06-19:33:08 applied
    units:message/0 cond {u'life': {u'$ne': 2}}
    statuses:u#message/0 update {u'$set': {u'status': u'installed', u'statusdata': {}, u'statusinfo': u''}}
  2014/03/06-19:33:08 applied
    units:message/0 update {u'$pull': {u'ports': {u'protocol': u'tcp', u'number': 55672}}}
  2014/03/06-19:33:09 applied
    units:message/0 update {u'$addToSet': {u'ports': {u'protocol': u'tcp', u'number': 5671}}}
  2014/03/06-19:33:13 applied
    units:message/0 cond {u'life': {u'$ne': 2}}
    statuses:u#message/0 update {u'$set': {u'status': u'started', u'statusdata': {}, u'statusinfo': u''}}
  2014/03/06-19:33:13 applied
    units:message/0 cond {u'life': 0}
    relations:message:cluster update {u'$inc': {u'unitcount': 1}}
    settings:r#198#peer#message/0 create {u'private-address': u'10.0.3.215'}
    relationscopes:r#198#peer#message/0 create {u'_id': u'r#198#peer#message/0'}
  2014/03/06-19:33:43 applied
    units:identity/0 cond {u'life': 0}
    relations:identity:cluster update {u'$inc': {u'unitcount': 1}}
    settings:r#197#peer#identity/0 create {u'private-address': u'10.0.3.80'}
    relationscopes:r#197#peer#identity/0 create {u'_id': u'r#197#peer#identity/0'}
  2014/03/06-19:33:52 applied
    units:identity/0 cond {u'life': 0}
    relations:identity:shared-db db:shared-db update {u'$inc': {u'unitcount': 1}}
    settings:r#200#requirer#identity/0 create {u'private-address': u'10.0.3.80'}
    relationscopes:r#200#requirer#identity/0 create {u'_id': u'r#200#requirer#identity/0'}
  2014/03/06-19:33:52 applied
    units:db/0 cond {u'life': 0}
    relations:identity:shared-db db:shared-db update {u'$inc': {u'unitcount': 1}}
    settings:r#200#provider#db/0 create {u'private-address': u'10.0.3.225'}
    relationscopes:r#200#provider#db/0 create {u'_id': u'r#200#provider#db/0'}
  2014/03/06-19:33:52 applied
    units:message/0 cond {u'life': 0}
    relations:meter:amqp message:amqp update {u'$inc': {u'unitcount': 1}}
    settings:r#199#provider#message/0 create {u'private-address': u'10.0.3.215'}
    relationscopes:r#199#provider#message/0 create {u'_id': u'r#199#provider#message/0'}
  2014/03/06-19:33:53 applied
    settings:r#199#provider#message/0 update {u'$set': {u'hostname':
    u'10.0.3.215', u'ssl_port': u'5671', u'ssl_ca':'value_omitted'}
    u'$unset': {}}


Available helper commands

    - units
    - unit
    - services
    - service
    - machines
    - machine
    - relations
    - relation
    - charms


