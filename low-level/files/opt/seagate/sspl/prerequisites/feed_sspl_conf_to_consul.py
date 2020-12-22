#!/usr/bin/env python3

# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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

"""
 ******************************************************************************
  Description:   Parse config file and arguments to set common & SSPL config
  Purpose    :   To feed sspl and common configuration to consul
  Usage      :   python3 feed_sspl_conf_to_consul.py [-F] [-C] [-N] [-Ru] [-Rp]
 ******************************************************************************
"""

import os
import sys
import consul
import argparse
from configobj import ConfigObj

from cortx.utils.process import SimpleProcess

CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'


class LoadConfig(object):

    def __init__(self):
        """ Establish consul connection
        """
        host = os.getenv('CONSUL_HOST', CONSUL_HOST)
        port = os.getenv('CONSUL_PORT', CONSUL_PORT)
        self.consul_conn = consul.Consul(host=host, port=port)
        self.rmq_same_pass_sect = ["LOGGINGPROCESSOR",
                                   "RABBITMQEGRESSPROCESSOR",
                                   "RABBITMQINGRESSPROCESSOR"]
        self.common_config_sect = ['system_information',
                                   'storage_enclosure',
                                   'bmc',
                                   'rabbitmq']
        self.cluster_id = None
        super().__init__()

    def _get_result(self, cmd):
        """ Execute command and return output
        """
        result = ""
        out, _, rc = SimpleProcess(cmd).run()
        if rc == 0:
            result = out.decode('utf-8').strip()
        return result

    def _insert_nested_dict_to_consul(self, v, prefix=''):
        """ Parse v and insert kv in consul
        """
        if isinstance(v, dict):
            for k, v2 in v.items():
                p2 = "{}/{}".format(prefix, k)
                self._insert_nested_dict_to_consul(v2, p2)
        elif isinstance(v, list):
            for i, v2 in enumerate(v):
                p2 = "{}/{}".format(prefix, i)
                self._insert_nested_dict_to_consul(v2, p2)
        else:
            if self.consul_conn is not None:
                self.consul_conn.kv.put(prefix, str(v))
            else:
                print('Consul connection issue, consul_conn is None. Exiting..')
                sys.exit()

    def set_config(self, filename, node, component=None, rmq_user=None, rmq_passwd=None,\
                    primary_mc=None, secondary_mc=None, primary_mc_port=None, secondary_mc_port=None,\
                    mc_user=None, mc_passwd=None, bmc_ip=None, bmc_user=None, bmc_passwd=None,\
                    storage_type=None, server_type=None):
        """ Read config file and insert common config and sspl config
        """
        try:
            if self.consul_conn is None:
                raise Exception(f"Failed to establish connection to {CONSUL_HOST}:{CONSUL_PORT}")
        except Exception as cerror:
            print("Error in connecting consul | consul: {}".format(cerror))
            print("Exiting...")
            sys.exit(os.EX_USAGE)
        else:
            parser = ConfigObj(filename, list_values=False)
            # Update same value to unique keys in consul
            if rmq_user and rmq_passwd:
                for key in self.rmq_same_pass_sect:
                    parser[key]['password'] = rmq_passwd
                    parser[key]['username'] = rmq_user
            # Include common configuration
            parser['SYSTEM_INFORMATION']['kernel_version'] = self._get_result('uname -r')
            cluster_id = self._get_result('consul kv get system_information/cluster_id')
            parser['SYSTEM_INFORMATION']['cluster_id'] = cluster_id or self._get_result('uuidgen')
            node_id = self._get_result(f'consul kv get system_information/{node}/node_id')
            parser['SYSTEM_INFORMATION']['storage_type'] = storage_type
            parser['SYSTEM_INFORMATION']['server_type'] = server_type
            # Storage enclosure information
            parser['STORAGE_ENCLOSURE'] = {'controller': {
                                                'user': mc_user,
                                                'password': mc_passwd,
                                                'primary_mc': {
                                                    'ip': primary_mc,
                                                    'port': primary_mc_port
                                                },
                                                'secondary_mc': {
                                                    'ip': secondary_mc,
                                                    'port': secondary_mc_port
                                                }
                                            }
                                        }
            # BMC information
            parser['BMC'] = { node: {
                                'ip': bmc_ip or self._get_result(f'consul kv get bmc/{node}/ip'),
                                'user': bmc_user or self._get_result(f'consul kv get bmc/{node}/user'),
                                'secret': bmc_passwd or self._get_result(f'consul kv get bmc/{node}/secret')
                                }
                            }
            prefix = component.lower() + '/config/'
            for k, v in parser.items():
                if k.lower() in self.common_config_sect:
                    self._insert_nested_dict_to_consul(v, prefix=k.lower())
                k = prefix + k
                self._insert_nested_dict_to_consul(v, prefix=k)


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(
        usage = "%(prog)s [-h] [-F] [-C] [-N] [-Ru] [-Rp] [-A] [-B] \
                    [-Ap] [-Bp] [-U] [-P] [--bmc_ip] [--bmc_user] [--bmc_passwd]",
        formatter_class = argparse.RawDescriptionHelpFormatter)
    argParser.add_argument("-F", "--file", help="Config file path")
    argParser.add_argument("-C", "--component", help="Keys will be stored with this prefix")
    argParser.add_argument("-N", "--node", help="Node name")
    argParser.add_argument("-Ru", "--rmq_user", default="sspluser", help="Rabbitmq username")
    argParser.add_argument("-Rp", "--rmq_passwd", default="", help="Rabbitmq password")
    argParser.add_argument("-A", "--primary_mc", default="10.0.0.2", help="Controller-A IP")
    argParser.add_argument("-B", "--secondary_mc", default="10.0.0.3", help="Controller-B IP")
    argParser.add_argument("-Ap", "--primary_mc_port", default="80", help="Controller-A Port")
    argParser.add_argument("-Bp", "--secondary_mc_port", default="80", help="Controller-B Port")
    argParser.add_argument("-U", "--user", default="", help="Controller Username")
    argParser.add_argument("-P", "--passwd", default="", help="Controller Password")
    argParser.add_argument("--bmc_ip", default="", help="BMC IP")
    argParser.add_argument("--bmc_user", default="", help="BMC User")
    argParser.add_argument("--bmc_passwd", default="", help="BMC Password")
    argParser.add_argument("-St", "--storage_type", default="virtual", help="Storage Type")
    argParser.add_argument("-Sr", "--server_type", default="virtual", help="Server Type")
    args = argParser.parse_args()
    sc = LoadConfig()
    # Load configs in consul
    sc.set_config(filename=args.file,
                  node=args.node,
                  component= args.component,
                  rmq_user=args.rmq_user,
                  rmq_passwd=args.rmq_passwd,
                  mc_user=args.user,
                  mc_passwd=args.passwd,
                  primary_mc=args.primary_mc,
                  secondary_mc=args.secondary_mc,
                  primary_mc_port=args.primary_mc_port,
                  secondary_mc_port=args.secondary_mc_port,
                  bmc_ip=args.bmc_ip,
                  bmc_user=args.bmc_user,
                  bmc_passwd=args.bmc_passwd,
                  storage_type=args.storage_type,
                  server_type=args.server_type)
