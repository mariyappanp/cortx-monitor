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

import time
from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from common import check_sspl_ll_is_running


UUID="16476007-a739-4785-b5c6-f3de189cdf12"

def init(args):
    pass

def test_node_psu_module_actuator(agrs):
    check_sspl_ll_is_running()
    instance_id = "*"
    psu_actuator_message_request("NDHW:node:fru:psu", instance_id)
    psu_module_actuator_msg = None
    ingressMsg = {}
    for i in range(30):
        if world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            time.sleep(1)
        while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
            time.sleep(0.1)
            print("Received: %s " % ingressMsg)
            try:
                # Make sure we get back the message type that matches the request
                msg_type = ingressMsg.get("actuator_response_type")
                if msg_type["info"]["resource_type"] == "node:fru:psu" and \
                    msg_type["instance_id"] == instance_id:
                    # Break if condition is satisfied.
                    psu_module_actuator_msg = msg_type
                    break
            except Exception as exception:
                time.sleep(0.1)
                print(exception)
        if psu_module_actuator_msg:
            break

    assert(ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID)
    assert(psu_module_actuator_msg is not None)
    assert(psu_module_actuator_msg.get("alert_type") is not None)
    assert(psu_module_actuator_msg.get("severity") is not None)
    assert(psu_module_actuator_msg.get("host_id") is not None)
    assert(psu_module_actuator_msg.get("info") is not None)
    assert(psu_module_actuator_msg.get("instance_id") == instance_id)

    psu_module_info = psu_module_actuator_msg.get("info")
    assert(psu_module_info.get("site_id") is not None)
    assert(psu_module_info.get("node_id") is not None)
    assert(psu_module_info.get("rack_id") is not None)
    assert(psu_module_info.get("resource_type") is not None)
    assert(psu_module_info.get("event_time") is not None)
    assert(psu_module_info.get("resource_id") is not None)

    fru_specific_infos = psu_module_actuator_msg.get("specific_info")
    assert(fru_specific_infos is not None)

    for fru_specific_info in fru_specific_infos:
        assert(fru_specific_info is not None)
        if fru_specific_info.get("ERROR"):
            # Skip any validation on specific info if ERROR seen on FRU
            continue
        assert(fru_specific_info.get("resource_id") is not None)
        resource_id = fru_specific_info.get("resource_id")
        if fru_specific_info.get(resource_id):
            assert(fru_specific_info.get(resource_id).get("ERROR") is not None)
            # Skip any validation on specific info if ERROR seen on sensor
            continue
        assert(fru_specific_info.get("States Asserted") is not None)
        assert(fru_specific_info.get("Sensor Type (Discrete)") is not None)


def psu_actuator_message_request(resource_type, instance_id):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message" : {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0",
                "uuid": UUID
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "node_id": "1"
            },
            "response_dest": {},
            "actuator_request_type": {
                "node_controller": {
                    "node_request": resource_type,
                    "resource": instance_id
                }
            }
        }
    }
    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(EgressProcessorTests.name(), egressMsg)

test_list = [test_node_psu_module_actuator]
