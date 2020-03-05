# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

def init(args):
    pass

def test_disk_space_alert(agrs):
    check_sspl_ll_is_running()
    disk_space_data_sensor_request("node:os:disk_space")
    disk_space_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(4)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:os:disk_space":
                disk_space_sensor_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(disk_space_sensor_msg is not None)
    assert(disk_space_sensor_msg.get("alert_type") is not None)
    assert(disk_space_sensor_msg.get("alert_id") is not None)
    assert(disk_space_sensor_msg.get("severity") is not None)
    assert(disk_space_sensor_msg.get("host_id") is not None)
    assert(disk_space_sensor_msg.get("info") is not None)
    assert(disk_space_sensor_msg.get("specific_info") is not None)

    disk_space_info = disk_space_sensor_msg.get("info")
    assert(disk_space_info.get("site_id") is not None)
    assert(disk_space_info.get("node_id") is not None)
    assert(disk_space_info.get("cluster_id") is not None)
    assert(disk_space_info.get("rack_id") is not None)
    assert(disk_space_info.get("resource_type") is not None)
    assert(disk_space_info.get("event_time") is not None)
    assert(disk_space_info.get("resource_id") is not None)

    disk_space_specific_info = disk_space_sensor_msg.get("specific_info")
    assert(disk_space_specific_info is not None)
    assert(disk_space_specific_info.get("freeSpace") is not None)
    assert(disk_space_specific_info.get("totalSpace") is not None)
    assert(disk_space_specific_info.get("diskUsedPercentage") is not None)

def check_sspl_ll_is_running():
    # Check that the state for sspl_ll service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_ll_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()


def disk_space_data_sensor_request(sensor_type):
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
                "msg_version": "1.0.0"
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "sensor_request_type": {
                "node_data": {
                    "sensor_type": sensor_type
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_disk_space_alert]