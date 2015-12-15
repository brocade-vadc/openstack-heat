#!/usr/bin/env python

from heat.engine import resource
from services_director import ServicesDirector
from time import sleep
from vtm import vTM
import yaml


class BrocadeResource(resource.Resource):

    def __init__(self, name, json_snippet, stack):
        super(BrocadeResource, self).__init__(name, json_snippet, stack)
        self._load_config()
        self.services_directors = [
            ServicesDirector(
                "https://%s:%s/api/tmcm/2.0" % (
                    server, self.config["services_director_port"]
                ),
                self.config["username"],
                self.config["password"],
                False,
                connectivity_test_url="https://%s:%s/api/tmcm/1.5" % (
                    server, self.config["services_director_port"]
                )
            )
            for server in self.config["services_directors"]
        ]

    def _load_config(self):
        with open("/etc/heat/brocade.yaml") as f:
            self.config = yaml.load(f.read())
        # If a list of available options and a specific option for a
        # given setting are both provided, be as restrictive as possible...
        if self.config.get("bandwidth_options") \
        and self.config.get("bandwidth"):
            del self.config["bandwidth_options"]
        if self.config.get("feature_pack_options") \
        and self.config.get("feature_pack"):
            del self.config["feature_pack_options"]

    def _get_services_director(self):
        """
        Gets available instance of Brocade Services Director from the cluster.
        """
        for services_director in self.services_directors:
            for _ in range(3):
                if services_director.test_connectivity():
                    return services_director
                sleep(2)
        raise Exception("Could not contact any Services Directors")

    def _get_vtm(self, server_id):
        """
        Gets available instance of Brocade vTM from a Services Director.
        """
        services_director = self._get_services_director()
        url = "%s/instance/%s/tm/3.5" % (
            services_director.instance_url,
            server_id
        )
        for i in xrange(5):
            vtm = vTM(url, self.config["username"], self.config["password"],
                      connectivity_test_url="%s/instance/%s/tm/3.5" % (
                          services_director.connectivity_test_url, server_id
                      )
            )
            try:
                if not vtm.test_connectivity():
                    raise Exception("")
                return vtm
            except:
                pass
            sleep(i)
        raise Exception("Could not contact vTM instance '%s'" % server_id)

