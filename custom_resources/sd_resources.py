#!/usr/bin/env python

from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties
from brocade_vadc_resource import BrocadeResource
from time import sleep
from vtm import vTM

from heat.openstack.common import log as logging
LOG = logging.getLogger(__name__)

class Instance(BrocadeResource):

    PROPERTIES = (
        SERVER_ID, HOSTNAME, MGMT_IP, USERNAME, PASSWORD, BANDWIDTH,
        FEATURE_PACK
    ) = (
        "server_id", "hostname", "mgmt_ip", "username", "password",
        "bandwidth", "feature_pack"
    )

    properties_schema = {
        SERVER_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of the Nova server instance being registered.'),
            update_allowed=False,
            required=True
        ),
        HOSTNAME: properties.Schema(
            properties.Schema.STRING,
            _('Hostname of the instance (used as the instance "tag").'),
            update_allowed=False,
            required=True
        ),
        MGMT_IP: properties.Schema(
            properties.Schema.STRING,
            _('IP address of the management interface.'),
            update_allowed=False,
            required=True
        ),
        USERNAME: properties.Schema(
            properties.Schema.STRING,
            _('Administrator username.'),
            update_allowed=False,
            default="admin"
        ),
        PASSWORD: properties.Schema(
            properties.Schema.STRING,
            _('Administrator password.'),
            update_allowed=False,
            required=True
        ),
        BANDWIDTH: properties.Schema(
            properties.Schema.STRING,
            _('Instance bandwidth allocation.'),
            update_allowed=True,
            required=False
        ),
        FEATURE_PACK: properties.Schema(
            properties.Schema.STRING,
            _('vTM feature pack.'),
            update_allowed=True,
            required=False
        )
    }

    def handle_create(self):
        self._register_instance()
        return self.properties["server_id"]

    def check_create_complete(self, instance_id):
        services_director = self._get_services_director()
        if services_director.unmanaged_instance.get(instance_id):
            return True
        else:
            return False

    def handle_delete(self):
        services_director = self._get_services_director()
        try:
            services_director.unmanaged_instance.delete(
                self.properties["server_id"]
            )
        except:
            pass

    def _await_instance_rest_enabled(self):
        services_director = self._get_services_director()
        url = "%s/instance/%s/tm/3.5" % (
            services_director.connectivity_test_url,
            self.properties["hostname"]
        )
        vtm = vTM(url, self.config["username"], self.config["password"])
        for counter in xrange(15):
            try:
                if not vtm.test_connectivity():
                    raise Exception("")
                return vtm
            except Exception:
                pass
            sleep(10)
        raise Exception("Timeout waiting for vTM instance to become available")

    def _register_instance(self):
        LOG.info("\n\n_register_instance()\n")
        LOG.info("\n\n%s\n" % self.properties["server_id"])
        services_director = self._get_services_director()
        instance = services_director.unmanaged_instance.get(
            self.properties["hostname"]
        )
        LOG.info("\n\nGot instance %s\n" % instance)
        if instance:
            LOG.info("\n\nDeleting...\n")
            instance = services_director.unmanaged_instance.delete(
                self.properties["hostname"]
            )
        LOG.info("\n\nCreating...\n")
        instance = services_director.unmanaged_instance.create(
            self.properties["server_id"],
            tag=self.properties["hostname"],
            admin_username=self.properties["username"],
            admin_password=self.properties["password"],
            management_address=self.properties["mgmt_ip"],
            rest_enabled=False,
            owner=self.stack.stack_user_project_id,
            bandwidth=self.get_bandwidth(),
            stm_feature_pack=self.get_feature_pack()
        )
        instance.start()
        self._await_instance_rest_enabled()
        instance.rest_enabled = True
        instance.license_name = "universal_v3"
        instance.update()

    def get_bandwidth(self):
        if self.config.get("bandwidth"):
            bandwidth = self.config["bandwidth"]
        elif not self.properties.get("bandwidth"):
            raise Exception("You must specify a bandwidth for the instance")
        elif int(self.properties["bandwidth"]) in \
        self.config["bandwidth_options"]:
            bandwidth = self.properties["bandwidth"]
        else:
            raise Exception("Invalid bandwidth choice - must be one of %s" % (
                ", ".join([str(bw) for bw in self.config["bandwidth_options"]])
            ))
        return int(bandwidth)

    def get_feature_pack(self):
        if self.config.get("feature_pack"):
            feature_pack = self.config["feature_pack"]
        elif not self.properties.get("feature_pack"):
            raise Exception("You must specify a feature_pack for the instance")
        elif self.properties["feature_pack"] in \
        self.config["feature_pack_options"]:
            feature_pack = self.properties["feature_pack"]
        else:
            raise Exception(
                "Invalid feature_pack choice - must be one of %s" % (
                    ", ".join(
                        [str(bw) for bw in self.config["feature_pack_options"]]
                    )
            ))
        return feature_pack


def resource_mapping():
    return {'Brocade::ServicesDirector::Instance': Instance}
