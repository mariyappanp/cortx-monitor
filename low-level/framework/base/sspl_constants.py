#!/usr/bin/python3.6

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

import configparser
import subprocess
import ast
import sys
import os
from enum import Enum

# Add the top level directories
sys.path.insert(0, '/opt/seagate/cortx/sspl/low-level')
from framework.utils.salt_util import SaltInterface
from framework.utils.service_logging import logger


PRODUCT_NAME = 'LDR_R2'
PRODUCT_FAMILY = 'cortx'
enabled_products = ["CS-A", "SINGLE","DUAL", "CLUSTER", "LDR_R1", "LDR_R2"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
setups = ["cortx"]
RESOURCE_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/low-level/json_msgs/schemas/"
CLI_RESOURCE_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/low-level/tests/manual"
DATA_PATH = f"/var/{PRODUCT_FAMILY}/sspl/data/"
SSPL_CONFIGURED=f"/var/{PRODUCT_FAMILY}/sspl/sspl-configured"
RESOURCE_HEALTH_VIEW = "/usr/bin/resource_health_view"
CONSUL_DUMP = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/bin/consuldump.py"
NODE_ID = "001"
SITE_ID = "001"
RACK_ID = "001"
SSPL_STORE_TYPE = 'file'
SYSLOG_HOST = 'localhost'
SYSLOG_PORT = '514'
SYSINFO = "SYSTEM_INFORMATION"
PRODUCT = "product"
SETUP = "setup"
MAX_CONSUL_RETRY = 12
WAIT_BEFORE_RETRY = 5
SUPPORT_REQUESTOR_NAME = "cortx-support"
SUPPORT_EMAIL_ID = "support@seagate.com"
SUPPORT_CONTACT_NUMBER = "18007324283"
ENCL_TRIGGER_LOG_MAX_RETRY = 10
ENCL_DOWNLOAD_LOG_MAX_RETRY = 60
ENCL_DOWNLOAD_LOG_WAIT_BEFORE_RETRY = 15

# required only for init
component = 'sspl/config'
file_store_config_path = '/etc/sspl.conf'
salt_provisioner_pillar_sls = 'sspl'
salt_uniq_attr_per_node = ['cluster_id']
salt_uniq_passwd_per_node = ['RABBITMQINGRESSPROCESSOR', 'RABBITMQEGRESSPROCESSOR', 'LOGGINGPROCESSOR']

# Initialize to default values
node_key_id = 'srvnode-1'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'

# TODO Keep only constants in this file.
# other values(configs) should come from cofig.
# Check if SSPL is configured
if os.path.exists(SSPL_CONFIGURED):
    try:
        config = configparser.ConfigParser()
        config.read(file_store_config_path)
        storage_type = config['STORAGE_ENCLOSURE']['type']
        server_type = config['SYSTEM_INFORMATION']['type']
        cluster_id = config['SYSTEM_INFORMATION']['cluster_id']
        node_id = config['SYSTEM_INFORMATION']['node_id']
        node_key_id = config['SYSTEM_INFORMATION']['salt_minion_id']
        CONSUL_HOST = config['DATASTORE']['consul_host']
        CONSUL_PORT = config['DATASTORE']['consul_port']
    except Exception as err:
        print(f'sspl_constants : Failed to read from {file_store_config_path} due to error - {err}')
# If not configured, use salt interface
else:
    try:
        salt_int = SaltInterface()
        node_key_id = salt_int.get_node_id()
        CONSUL_HOST = salt_int.get_consul_vip()
        CONSUL_PORT = salt_int.get_consul_port()
    except Exception as err:
        print(f'sspl_constants : Failed to read from SaltInterface due to error - {err}')

CONSUL_ERR_STRING = '500 No cluster leader'

SSPL_SETTINGS = {
        "REALSTORSENSORS": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["RealStorFanSensor", "RealStorPSUSensor",
                "RealStorControllerSensor", "RealStorDiskSensor", "RealStorSideplaneExpanderSensor",
                "RealStorLogicalVolumeSensor", "RealStorEnclosureSensor"],
        },
        "NODEHWSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [ "NodeHWsensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": [ "NodeHWsensor"],
        },
        "SYSTEMDWATCHDOG": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [],
            "MESSAGE_HANDLERS": [],
            "SENSORS": [],
        },
        "RAIDSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["RAIDsensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["RAIDsensor", "RAIDIntegritySensor"],
        },
        "SASPORTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["SASPortSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["SASPortSensor"],
        },
        "MEMFAULTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["MemFaultSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["MemFaultSensor"],
        },
        "CPUFAULTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["CPUFaultSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["CPUFaultSensor"],
        },

        "_ENABLE_ALWAYS": {
            "ACTUATORS" : ["Service", "RAIDactuator", "Smartctl", "NodeHWactuator", "RealStorActuator"],
            "CORE_PROCESSORS" : ("RabbitMQegressProcessor", "RabbitMQingressProcessor", "LoggingProcessor"),
            "DEGRADED_STATE_MODULES" : ("ServiceWatchdog", "NodeData", "IEMSensor",
                "DiskMsgHandler", "LoggingMsgHandler", "ServiceMsgHandler", "NodeDataMsgHandler",
                "NodeControllerMsgHandler"),
            "MESSAGE_HANDLERS" : ("DiskMsgHandler", "LoggingMsgHandler", "ServiceMsgHandler", "NodeDataMsgHandler",
                "NodeControllerMsgHandler", "RealStorEnclMsgHandler", "RealStorActuatorMsgHandler"),
            "SENSORS" : ["ServiceWatchdog", "NodeData",  "IEMSensor"]
        }
}

# The keys which are actually active
sspl_settings_configured_groups = set()

if SSPL_STORE_TYPE == 'consul':
    COMMON_CONFIGS = {
        "SYSTEM_INFORMATION": {
            "sspl_key" : "key_provided_by_provisioner",
            "operating_system" : "operating_system",
            "kernel_version" : "kernel_version",
            "product" : "product",
            "site_id" : "site_id",
            "rack_id" : "rack_id",
            "node_id" : f"{node_key_id}/node_id",
            "cluster_id" : "cluster_id",
            "syslog_host" : "syslog_host",
            "syslog_port" : "syslog_port",
            "setup" : "setup",
            "data_path" : "data_path"
        },
        "STORAGE_ENCLOSURE": {
            "sspl_key" : "key_provided_by_provisioner",
            "primary_controller_ip" : "controller/primary_mc/ip",
            "primary_controller_port" : "controller/primary_mc/port",
            "secondary_controller_ip" : "controller/secondary_mc/ip",
            "secondary_controller_port" : "controller/secondary_mc/port",
            "user" : "controller/user",
            "password" : "controller/secret",
            "mgmt_interface" : "controller/mgmt_interface"
        },
        "RABBITMQCLUSTER": {
            "sspl_key" : "key_provided_by_provisioner",
            "cluster_nodes" : "rabbitmq/cluster_nodes",
            "erlang_cookie" : "rabbitmq/erlang_cookie"
        },
        "BMC": {
            "sspl_key" : "key_provided_by_provisioner",
            f"ip_{node_key_id}" : f"{node_key_id}/ip",
            f"user_{node_key_id}" : f"{node_key_id}/user",
            f"secret_{node_key_id}" : f"{node_key_id}/secret"
        }
    }
else:
    COMMON_CONFIGS = {
        "SYSTEM_INFORMATION": {
            "sspl_key" : "key_provided_by_provisioner",
            "operating_system" : "operating_system",
            "kernel_version" : "kernel_version",
            "product" : "product",
            "site_id" : "site_id",
            "rack_id" : "rack_id",
            "node_id" : "node_id",
            "cluster_id" : "cluster_id",
            "syslog_host" : "syslog_host",
            "syslog_port" : "syslog_port",
            "setup" : "setup",
            "data_path" : "data_path"
        },
        "STORAGE_ENCLOSURE": {
            "sspl_key" : "key_provided_by_provisioner",
            "primary_controller_ip" : "primary_controller_ip",
            "primary_controller_port" : "primary_controller_port",
            "secondary_controller_ip" : "secondary_controller_ip",
            "secondary_controller_port" : "secondary_controller_port",
            "user" : "user",
            "password" : "password",
            "mgmt_interface" : "mgmt_interface"
        },
        "RABBITMQCLUSTER": {
            "sspl_key" : "key_provided_by_provisioner",
            "cluster_nodes" : "cluster_nodes",
            "erlang_cookie" : "erlang_cookie"
        },
        "BMC": {
            "sspl_key" : "key_provided_by_provisioner",
            f"ip" : f"ip",
            f"user" : f"user",
            f"secret" : f"secret"
        }
    }


SSPL_CONFIGS = ['log_level', 'cli_type', 'sspl_log_file_path', 'cluster_id', 'storage_enclosure', 'setup', 'operating_system']


class RaidDataConfig(Enum):
    MDSTAT_FILE = "/proc/mdstat"
    DIR = "/sys/block/"
    SYNC_ACTION_FILE = "/md/sync_action"
    MISMATCH_COUNT_FILE = "/md/mismatch_cnt"
    STATE_COMMAND_RESPONSE = 'idle'
    MISMATCH_COUNT_RESPONSE = '0'
    RAID_RESULT_DIR = "/tmp"
    RAID_RESULT_FILE_PATH = "/tmp/result_raid_health_file"
    RAID_MISMATCH_FAULT_STATUS = "mismatch_cnt_fault_status"
    MAX_RETRIES = 10
    NEXT_ITERATION_TIME = 3600
    PRIORITY = 1

class RaidAlertMsgs(Enum):
    MISMATCH_MSG = "MISMATCH COUNT is found, as count does not match to the default '0' value."


class AlertTypes(Enum):
    GET = "get"
    FAULT = "fault"


class SensorTypes(Enum):
    TEMPERATURE = "temperature"
    CURRENT = "current"
    VOLTAGE = "voltage"


class SeverityTypes(Enum):
    INFORMATIONAL = "informational"


class ResourceTypes(Enum):
    SENSOR = "sensor"
    INTERFACE = "interface"


class EnclInterface(Enum):
    SAS = "SAS"

class StoreTypes(Enum):
    FILE = "file"
    CONSUL = "consul"

class ServiceTypes(Enum):
    RABBITMQ = "rabbitmq"
    STORAGE_ENCLOSURE = "storage_enclosure"
    CLUSTER = "cluster"

class OperatingSystem(Enum):
    CENTOS7 = "centos7"
    CENTOS6 = "centos6"
    RHEL7 = "rhel7"
    RHEL6 = "rhel6"
    OSX = "osX"

iem_severity_types = {
    "A": "alert",
    "X": "critical",
    "E": "error",
    "W": "warning",
    "N": "notice",
    "C": "configuration",
    "I": "informational",
    "D": "detail",
    "B": "debug"
}

iem_severity_to_alert_mapping = {
    "A": AlertTypes.FAULT.value,
    "X": AlertTypes.FAULT.value,
    "E": AlertTypes.FAULT.value,
    "W": AlertTypes.GET.value,
    "N": AlertTypes.GET.value,
    "C": AlertTypes.GET.value,
    "I": AlertTypes.GET.value,
    "D": AlertTypes.GET.value,
    "B": AlertTypes.GET.value
}

iem_source_types = {
    "H": "Hardware",
    "S": "Software",
    "F": "Firmware",
    "O": "OS"
}

if __name__ == "__main__":
    print(' '.join(enabled_products))
