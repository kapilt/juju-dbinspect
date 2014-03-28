import argparse
import code
import functools
import logging
import pprint
import sys

from juju_dbinspect.config import Config
from juju_dbinspect.exceptions import ConfigError
from juju_dbinspect.entities import (
    machines, machine, units, unit, services, service, relations, history,
    shell_commands)
from juju_dbinspect.identity import is_unit, is_service, is_machine

log = logging.getLogger("juju-db")

PLUGIN_DESCRIPTION = "Juju database introspection"


def setup_parser():
    if '--description' in sys.argv:
        print(PLUGIN_DESCRIPTION)
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="%s\n%s" % (PLUGIN_DESCRIPTION, invoke_action.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-e", "--environment", help="Juju environment to operate on")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output")

    parser.add_argument("targets", nargs="+")

    return parser


def shell(client, db):
    ctxt = {'client': client, 'db': db}

    def bound_func(f):
        def wrapper(*args, **kw):
            return f(db, *args, **kw)
        return wrapper

    for f in shell_commands:
        bound = bound_func(f)
        functools.update_wrapper(bound, f)
        ctxt[f.__name__] = bound
    ctxt['pprint'] = pprint.pprint
    code.interact(local=ctxt, banner="Juju DB Shell")


def invoke_action(client, db, targets):
    """
    Drop into an interactive python shell::
      $ juju db shell

    Get the last n transactions (default 100) that have modified the
    environment.
      $ juju db history n

    Get the names of all the services in the system::
      $ juju db services

    Get the names of all the units in the system::
      $ juju db units

    Get the details on machine 0::
      $ juju db 0

    Get the details on the unit mysql/0::
      $ juju db mysql/0

    Get the details on the mysql service::
      $ juju db mysql

    Get the relation settings for the mysql/0 unit in the wordpress relation::
      $ juju db mysql/0 wordpress
    """
    if targets[0] == "shell":
        return shell(client, db)
    elif targets[0] == "units":
        return sorted(units(db))
    elif targets[0] == "relations":
        return sorted(relations(db))
    elif targets[0] == "machines":
        return sorted(machines(db))
    elif targets[0] == "services":
        return sorted(services(db))
    elif targets[0] == "history":
        return history(db)

    if len(targets) == 1:
        t = targets.pop()
        if is_machine(t):
            return machine(db, t).formatted
        elif is_unit(t):
            return unit(db, t).formatted
        elif is_service(t):
            return service(db, t).formatted
        else:
            raise ValueError("Unknown entity %s" % t)
    if len(targets) > 2:
        raise ValueError("Too many params %s" % (targets))
    left, right = targets
    if is_unit(left):
        unit_id = left
        service_name = right
    elif is_unit(right):
        unit_id = right
        service_name = left
    else:
        raise ValueError("Invalid params for unit relation %s" % targets)
    if not is_service(service_name):
        raise ValueError(
            "Invalid service and related unit spec %s" % targets)
    return unit(db, unit_id).relation_data(service_name)


def main():
    parser = setup_parser()
    options = parser.parse_args()
    config = Config(options)

    if config.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        datefmt="%Y/%m/%d %H:%M.%S",
        format="%(asctime)s:%(levelname)s %(message)s")

    logging.getLogger('requests').setLevel(level=logging.WARNING)

    try:
        log.debug("Connecting to database...")
        client, db = config.connect_db()
        log.debug("Connected to db")
    except ConfigError, e:
        print("Configuration error: %s" % str(e))
        sys.exit(1)

    import json
    try:
        log.debug("Invoking action")
        result = invoke_action(client, db, options.targets)
        if result is not None:
            print json.dumps(result, indent=2)
        log.debug("Action complete")
    except ValueError, e:
        print("Invalid paramaters: %s" % e)
        sys.exit(1)

if __name__ == '__main__':
    main()
