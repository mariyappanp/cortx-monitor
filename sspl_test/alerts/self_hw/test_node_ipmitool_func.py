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

# Connectivity to BMC is checked via SSPL during restart
# We can restart SSPL and wait for an alert from SSPL if there is a failure
# If there is no failure, that would mean connectivity is OK

import re

from cortx.utils.process import SimpleProcess


def init(args):
    pass

def test_ipmitool_version(args):
    """Check for expected ipmitool & IPMI version and v2 compliant."""
    expected_ipmitool_ver = "1.8.18"
    expected_ipmi_version = "2.0"
    expected_ipmi_compliant = "v2 compliant"
    # Check ipmitool version
    tool_ver_cmd = "ipmitool -V"    # ipmitool version 1.8.18
    print("Executing command: %s" % tool_ver_cmd)
    res_op, res_err, res_rc = SimpleProcess(tool_ver_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"ipmitool version[\s]+([\w.]+)(.*)", res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if version_found != expected_ipmitool_ver:
        print("Expected: %s Actual: %s" % (
            expected_ipmitool_ver, version_found))
        assert False

    # Check IPMI version
    ipmi_ver_cmd = "ipmitool bmc info"     # IPMI Version : 2.0
    res_op, res_err, res_rc = SimpleProcess(ipmi_ver_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"IPMI Version[\s]+:[\s]+([\w.]+)(.*)", res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if version_found != expected_ipmi_version:
        print("Expected: %s Actual: %s" % (
            expected_ipmi_version, version_found))
        assert False

    # Check IPMI v2 compliant
    ipmi_compliant = "ipmitool sel info"   # Version : 1.5 (v1.5, v2 compliant)
    res_op, res_err, res_rc = SimpleProcess(ipmi_compliant).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"Version[\s]+:[\s]+.*(%s).*" % expected_ipmi_compliant, res_op)
        if not search_res:
            raise Exception(
                "ERROR: IPMITOOL is not %s" % expected_ipmi_compliant)
    else:
        raise Exception("ERROR: %s" % res_err.decode())

def test_sensor_availability(args):
    """Fail if any expected sensor is not detected by ipmitool."""
    commands = {
        "Voltage sensors": "ipmitool sdr type Voltage",
        "Temperature sensors": "ipmitool sdr type Temperature",
        "Fan sensors": "ipmitool sdr type Fan",
        "Power Supply sensors": "ipmitool sdr type 'Power Supply'",
        "Power Unit sensors": "ipmitool sdr type 'Power Unit'",
        "Drive sensors": "ipmitool sdr type 'Drive Slot / Bay'"
    }
    # Get manufacturer name
    server_name = None
    bmc_info_cmd = "ipmitool bmc info"   # Manufacturer Name : Supermicro
    res_op, res_err, res_rc = SimpleProcess(bmc_info_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"Manufacturer Name[\s]+:[\s]+([\w.]+)(.*)", res_op)
        if search_res:
            server_name = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    assert(server_name is not None)
    for sensor, cmd in commands.items():
        res_op, res_err, res_rc = SimpleProcess(cmd).run()
        if res_rc == 0:
            res_op = res_op.decode().replace("\n", "")
            if not res_op:
                print(
                    "'%s' sensor is not seen in '%s' server." % (
                        sensor, server_name))
                assert(False)
        else:
            raise Exception("ERROR: %s" % res_err.decode())

def test_ipmitool_sel_accessibility(args):
    """Check sel list is accessible."""
    sel_command = "ipmitool sel list"
    res_op, res_err, res_rc = SimpleProcess(sel_command).run()
    if res_rc != 0:
        res_op = res_op.decode()


test_list = [
    test_ipmitool_version,
    test_sensor_availability,
    test_ipmitool_sel_accessibility
    ]
