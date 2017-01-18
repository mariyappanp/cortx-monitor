"""
 ****************************************************************************
 Filename:          plane_cntrl_rmq_egress_processor.py
 Description:       Handles outgoing messages via rabbitMQ over network
 Creation Date:     11/14/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import datetime
import json
import pika
import os

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.thread_controller import ThreadControllerMsg

import ctypes
try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("PlaneCntrlRMQegressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib=False


class PlaneCntrlRMQegressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ over network"""

    MODULE_NAME = "PlaneCntrlRMQegressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR       = MODULE_NAME.upper()
    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'
    VIRT_HOST               = 'virtual_host'
    USER_NAME               = 'username'
    PASSWORD                = 'password'
    PRIMARY_RABBITMQ        = 'primary_rabbitmq_server'
    SECONDARY_RABBITMQ      = 'secondary_rabbitmq_server'
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'


    @staticmethod
    def name():
        """ @return: name of the module."""
        return PlaneCntrlRMQegressProcessor.MODULE_NAME

    def __init__(self):
        super(PlaneCntrlRMQegressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlRMQegressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlRMQegressProcessor, self).initialize_msgQ(msgQlist)

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._msg_sent_succesfull = True

        # Configure RabbitMQ Exchange to transmit messages
        self._connection = None
        self._read_config()
        self._get_connection(host_addr=self._current_rabbitMQ_server)

        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                       (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # Block on message queue until it contains an entry
            if self._msg_sent_succesfull:
                # Only get a new msg if we've successfully processed the current one
                self._jsonMsg = self._read_my_msgQ()

            if self._jsonMsg is not None:
                self._transmit_msg_on_exchange()

            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                # Only get a new msg if we've successfully processed the current one
                if self._msg_sent_succesfull:
                    self._jsonMsg = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("PlaneCntrlRMQegressProcessor restarting")

            # Configure RabbitMQ Exchange to receive messages
            self._toggle_rabbitMQ_servers()
            self._get_connection(host_addr=self._current_rabbitMQ_server)

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown == True:
            self.shutdown()
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.QUEUE_NAME,
                                                                 'ras_status')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'ras_sspl')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')
            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')
            self._signature_user = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.SIGNATURE_USERNAME,
                                                                 'sspl-ll')
            self._signature_token = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.SIGNATURE_TOKEN,
                                                                 'FAKETOKEN1234')
            self._signature_expires = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.SIGNATURE_EXPIRES,
                                                                 "3600")
            self._primary_rabbitMQ_server   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.PRIMARY_RABBITMQ,
                                                                 'localhost')
            self._secondary_rabbitMQ_server = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.SECONDARY_RABBITMQ,
                                                                 'localhost')
            self._current_rabbitMQ_server = self._primary_rabbitMQ_server

        except Exception as ex:
            logger.exception("PlaneCntrlRMQegressProcessor, _read_config: %r" % ex)

    def _get_connection(self, host_addr):
        try:
            # ensure the rabbitmq queues/etc exist
            creds = pika.PlainCredentials(self._username, self._password)
            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=host_addr,
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            self._channel = self._connection.channel()
            try:
                self._channel.queue_declare(
                    queue=self._queue_name,
                    durable=True
                    )
            except Exception as e:
                logger.exception(e)
            try:
                self._channel.exchange_declare(
                    exchange=self._exchange_name,
                    type='topic',
                    durable=True
                    )
            except Exception as e:
                logger.exception(e)
            self._channel.queue_bind(
                queue=self._queue_name,
                exchange=self._exchange_name,
                routing_key=self._routing_key
                )
        except Exception as ex:
            logger.exception("PlaneCntrlRMQegressProcessor, _get_connection: %r" % ex)
            self._connection = None

    def _add_signature(self):
        """Adds the authentication signature to the message"""
        self._log_debug("_add_signature, jsonMsg: %s" % self._jsonMsg)
        self._jsonMsg["username"] = self._signature_user
        self._jsonMsg["expires"]  = int(self._signature_expires)
        self._jsonMsg["time"]     = str(datetime.datetime.now())

        if use_security_lib:
            authn_token_len = len(self._signature_token) + 1
            session_length  = int(self._signature_expires)
            token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())
    
            SSPL_SEC.sspl_generate_session_token(
                                    self._signature_user, authn_token_len, 
                                    self._signature_token, session_length, token)
    
            # Generate the signature
            msg_len = len(self._jsonMsg) + 1
            sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
            SSPL_SEC.sspl_sign_message(msg_len, str(self._jsonMsg), self._signature_user,
                                       token, sig)
    
            self._jsonMsg["signature"] = str(sig.raw)
        else:
            self._jsonMsg["signature"] = "SecurityLibNotInstalled"

    def _transmit_msg_on_exchange(self):
        """Transmit json message onto RabbitMQ exchange"""
        self._log_debug("_transmit_msg_on_exchange, jsonMsg: %s" % self._jsonMsg)

        try:
            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty 
            if self._jsonMsg.get("message").get("actuator_response_type") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") == \
                    "SSPL-LL is shutting down":
                    logger.info("RabbitMQegressProcessor, _transmit_msg_on_exchange, received" \
                                    "global shutdown message from sspl_ll_d")
                    self._request_shutdown = True

            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"

            self._add_signature()
            self._jsonMsg = json.dumps(self._jsonMsg).encode('utf8')
            self._get_connection(host_addr=self._current_rabbitMQ_server)
            self._channel.basic_publish(exchange=self._exchange_name,
                                routing_key=self._routing_key,
                                properties=msg_props,
                                body=str(self._jsonMsg))

            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            self._msg_sent_succesfull = True
            if self._connection is not None:
                self._connection.close()
                del(self._connection)

        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, _transmit_msg_on_exchange: %r" % ex)
            self._msg_sent_succesfull = False
            self._toggle_rabbitMQ_servers()

    def _toggle_rabbitMQ_servers(self):
        """Toggle between hosts when a connection fails"""
        if self._current_rabbitMQ_server == self._primary_rabbitMQ_server:
            self._current_rabbitMQ_server = self._secondary_rabbitMQ_server
        else:
            self._current_rabbitMQ_server = self._primary_rabbitMQ_server

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlRMQegressProcessor, self).shutdown()