from distutils.version import LooseVersion
import logging
import json
import subprocess
import os

import yaml

from pymongo import MongoClient

from juju_dbinspect.exceptions import ConfigError


VERSION_1_15 = LooseVersion("1.15.1")


class Config(object):

    def __init__(self, options):
        self.options = options

    def connect_db(self):
        """Return a websocket connection to the environment.
        """
        uri, password = self.get_db_uri()
        client = MongoClient(uri)
        client.admin.authenticate('admin', password)
        return client, client.juju

    def get_db_uri(self):
        env_data = self.get_env_state()
        env_name = self.get_env_name()
        # Prior to 1.17 or not bootstrapped
        if not env_data:
            version = self.get_version()
            if version > VERSION_1_15:
                output = subprocess.check_output(
                    ["juju", "api-endpoints", "--format", "json",
                     "-e", env_name])
                host, port = json.loads(output)[0].split(":", 1)
                env_data['bootstrap-host'] = host
            # Fallback to status parsing.
            else:
                output = subprocess.check_output(
                    ["juju", "status", "-e", env_name])
                host = yaml.safe_loads(output)['machines']['0']['dns-name']
                env_data['bootstrap-host'] = host
            env_conf = yaml.load(self.get_env_conf())['environments'][env_name]
            env_data['admin-secret'] = env_conf['admin-secret']
        # if 1.17/1.18 hack around juju (this changed without notice in 1.17.6
        elif 'state-servers' in env_data:
            # db password only stored in old-password of agent.conf
            # http://pad.lv/1270434 marked won't fix/opinion.. whatever.
            output = subprocess.check_output([
                "juju", "run", "-e", env_name, "--machine", "0",
                "sudo cat /var/lib/juju/agents/machine-0/agent.conf"])
            mdata = yaml.safe_load(output)
            env_data['admin-secret'] = mdata['oldpassword']
            env_data['bootstrap-host'] = env_data['state-servers'][
                0].split(":")[0]
        uri = "mongodb://%(bootstrap-host)s:37017/juju?w=1&ssl=true" % env_data
        logging.debug("Connecting to mongo @ %s" % uri)
        return uri, env_data['admin-secret']

    @property
    def verbose(self):
        return self.options.verbose

    @property
    def juju_home(self):
        return os.path.expanduser(
            os.environ.get("JUJU_HOME", "~/.juju"))

    def get_version(self):
        return LooseVersion(
            subprocess.check_output(["juju", "version"]).strip())

    def get_env_name(self):
        """Get the environment name.
        """
        if self.options.environment:
            return self.options.environment
        elif os.environ.get("JUJU_ENV"):
            return os.environ['JUJU_ENV']

        env_ptr = os.path.join(self.juju_home, "current-environment")
        if os.path.exists(env_ptr):
            with open(env_ptr) as fh:
                return fh.read().strip()

        with open(self.get_env_conf()) as fh:
            conf = yaml.safe_load(fh.read())
            if not 'default' in conf:
                raise ConfigError("No Environment specified")
            return conf['default']

    def get_env_conf(self):
        """Get the environment config file.
        """
        conf = os.path.join(self.juju_home, 'environments.yaml')
        if not os.path.exists(conf):
            raise ConfigError("Juju environments.yaml not found %s" % conf)
        return conf

    def get_env_state(self):
        conf = os.path.join(
            self.juju_home, 'environments', '%s.jenv' % self.get_env_name())
        if not os.path.exists(conf):
            return {}
        with open(conf) as fh:
            return yaml.load(fh.read())
