# Copyright 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import unittest
from unittest.mock import Mock
import tempfile
import os
import uuid

from collections import OrderedDict
from sawtooth_sdk.processor.config import get_log_config
from sawtooth_sdk.processor.config import get_log_dir
from sawtooth_sdk.processor.config import get_processor_config

from sawtooth_sdk.processor.context import Context
from sawtooth_sdk.messaging.future import Future
from sawtooth_sdk.messaging.future import FutureResult
from sawtooth_sdk.messaging.future import FutureCollection

from sawtooth_sdk.protobuf.validator_pb2 import Message
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateEntry
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateGetRequest
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateGetResponse
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateSetRequest
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateSetResponse
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateDeleteRequest
from sawtooth_sdk.protobuf.state_context_pb2 import TpStateDeleteResponse
from sawtooth_sdk.protobuf.state_context_pb2 import TpReceiptAddDataRequest
from sawtooth_sdk.protobuf.state_context_pb2 import TpReceiptAddDataResponse
from sawtooth_sdk.protobuf.state_context_pb2 import TpEventAddRequest
from sawtooth_sdk.protobuf.state_context_pb2 import TpEventAddResponse
from sawtooth_sdk.protobuf.events_pb2 import Event


class ContextTest(unittest.TestCase):
    def setUp(self):
        self.context_id = "test"
        self.mock_stream = Mock()
        self.context = Context(self.mock_stream, self.context_id)
        self.addresses = ["a", "b", "c"]
        self.data = [addr.encode() for addr in self.addresses]

    def _make_future(self, message_type, content):
        f = Future(self.context_id)
        f.set_result(FutureResult(
            message_type=message_type,
            content=content))
        return f

    def _make_entries(self, protobuf=True):
        if protobuf:
            return [
                TpStateEntry(address=a, data=d)
                for a, d in zip(self.addresses, self.data)
            ]

        entries = OrderedDict()
        for a, d in zip(self.addresses, self.data):
            entries[a] = d
        return entries

    def test_state_get(self):
        """Tests that State gets addresses correctly."""
        self.mock_stream.send.return_value = self._make_future(
            message_type=Message.TP_STATE_GET_RESPONSE,
            content=TpStateGetResponse(
                status=TpStateGetResponse.OK,
                entries=self._make_entries()).SerializeToString())

        self.context.get_state(self.addresses)

        self.mock_stream.send.assert_called_with(
            Message.TP_STATE_GET_REQUEST,
            TpStateGetRequest(
                context_id=self.context_id,
                addresses=self.addresses).SerializeToString())

    def test_state_set(self):
        """Tests that State sets addresses correctly."""
        self.mock_stream.send.return_value = self._make_future(
            message_type=Message.TP_STATE_SET_RESPONSE,
            content=TpStateSetResponse(
                status=TpStateSetResponse.OK,
                addresses=self.addresses).SerializeToString())

        self.context.set_state(self._make_entries(protobuf=False))

        self.mock_stream.send.assert_called_with(
            Message.TP_STATE_SET_REQUEST,
            TpStateSetRequest(
                context_id=self.context_id,
                entries=self._make_entries()).SerializeToString())

    def test_state_delete(self):
        """Tests that State deletes addresses correctly."""
        self.mock_stream.send.return_value = self._make_future(
            message_type=Message.TP_STATE_DELETE_RESPONSE,
            content=TpStateDeleteResponse(
                status=TpStateDeleteResponse.OK,
                addresses=self.addresses).SerializeToString())

        self.context.delete_state(self.addresses)

        self.mock_stream.send.assert_called_with(
            Message.TP_STATE_DELETE_REQUEST,
            TpStateDeleteRequest(
                context_id=self.context_id,
                addresses=self.addresses).SerializeToString())

    def test_add_receipt_data(self):
        """Tests that State adds receipt data correctly."""
        self.mock_stream.send.return_value = self._make_future(
            message_type=Message.TP_RECEIPT_ADD_DATA_RESPONSE,
            content=TpReceiptAddDataResponse(
                status=TpReceiptAddDataResponse.OK).SerializeToString())

        self.context.add_receipt_data(b"test")

        self.mock_stream.send.assert_called_with(
            Message.TP_RECEIPT_ADD_DATA_REQUEST,
            TpReceiptAddDataRequest(
                context_id=self.context_id,
                data=b"test").SerializeToString())

    def test_add_event(self):
        """Tests that State adds events correctly."""
        self.mock_stream.send.return_value = self._make_future(
            message_type=Message.TP_EVENT_ADD_RESPONSE,
            content=TpEventAddResponse(
                status=TpEventAddResponse.OK).SerializeToString())

        self.context.add_event("test", [("test", "test")], b"test")

        self.mock_stream.send.assert_called_with(
            Message.TP_EVENT_ADD_REQUEST,
            TpEventAddRequest(
                context_id=self.context_id,
                event=Event(
                    event_type="test",
                    attributes=[Event.Attribute(key="test", value="test")],
                    data=b"test")).SerializeToString())


class ConfigTest(unittest.TestCase):
    def test_get_dir(self):
        """Tests the return value of directory path based on
           configuration.
        """
        os.environ.clear()
        directory = tempfile.mkdtemp(prefix="test-path-config-")
        try:
            os.environ['SAWTOOTH_HOME'] = directory
            config_dir = os.path.join(directory, 'etc')
            os.mkdir(config_dir)
            filename = os.path.join(config_dir, 'path.toml')
            with open(filename, 'w') as fd:
                fd.write(" ")
            config = get_log_dir()
            sawtooth_home_dir = 'logs'
            self.assertEqual(config, os.path.join(os.environ['SAWTOOTH_HOME'],
                                                  sawtooth_home_dir))
        finally:
            pass

    def test_get(self):
        """Tests if the directory path is based on OS defaults.
        """
        os.name = "nt"
        config = get_log_dir()
        self.assertEqual(config, os.path.join('/usr', 'logs'))

    def test_get_log_config(self):
        """Tests if there is a log config file in the config directory
           and ends with .yaml extension.
       """
        os.environ.clear()
        directory = tempfile.mkdtemp(prefix="test-path-config-")
        try:
            os.environ['SAWTOOTH_HOME'] = directory
            config_dir = os.path.join(directory, 'logs')
            os.mkdir(config_dir)
            filename = os.path.join(config_dir, 'intkey_logs_config.yaml')
            with open(filename, 'w') as fd:
                fd.write(" ")
            config = get_log_config(filename)
            self.assertEqual(config, None)
        finally:
            pass

    def test_none_file(self):
        """Tests the function when log config file does not exist
           and returns None.
       """
        filename = None
        config = get_log_config(filename)
        self.assertEqual(config, None)

    def test_get_log_config_new(self):
        """Tests if log config file in the config directory
           does not end with .yaml extension.
       """
        os.environ.clear()
        directory = tempfile.mkdtemp(prefix="test-path-config-")
        try:
            os.environ['SAWTOOTH_HOME'] = directory
            config_dir = os.path.join(directory, 'logs')
            os.mkdir(config_dir)
            filename = os.path.join(config_dir, 'intkey_logs_config.yaml ')
            with open(filename, 'w') as fd:
                fd.write(" ")
            config = get_log_config(filename)
            self.assertEqual(config, {})
        finally:
            pass

    def test_get_processor_config(self):
        """Tests if there is a proccesor config in the config directory
           and returns it.
       """
        os.environ.clear()
        directory = tempfile.mkdtemp(prefix="test-path-config-")
        try:
            os.environ['SAWTOOTH_HOME'] = directory
            config_dir = os.path.join(directory, 'etc')
            os.mkdir(config_dir)
            filename = os.path.join(config_dir, 'path.toml')
            with open(filename, 'w') as fd:
                fd.write(" ")
                config = get_processor_config(filename)
                log_config = {}
                self.assertEqual(config, log_config)
        finally:
            pass


class FutureTest(unittest.TestCase):
    def test_future(self):
        """Tests the init() method and done() function.
        """
        obj = Future("")
        done = obj.done()
        bool_value = False
        self.assertEqual(done, bool_value)

    def test_futurecollection(self):
        """Tests the future_collection_method() initialize
           correlation id, put() and set_result() function.
        """
        obj = FutureCollection()
        correlation_id = uuid.uuid4().hex.encode()
        result = None
        obj1 = Future(correlation_id)
        obj.put(obj1)
        obj.set_result(correlation_id, result)
        self.assertEqual(result, None)
