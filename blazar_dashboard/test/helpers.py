#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django import http
from openstack_dashboard.test import helpers

from blazar_dashboard.test.test_data import utils


class TestCase(helpers.TestCase):
    def _setup_test_data(self):
        super(TestCase, self)._setup_test_data()
        utils.load_test_data(self)


class BaseAdminViewTests(helpers.BaseAdminViewTests):
    def _setup_test_data(self):
        super(BaseAdminViewTests, self)._setup_test_data()
        utils.load_test_data(self)


class IsA(object):
    """Class to compare param is a specified class."""
    def __init__(self, cls):
        self.cls = cls

    def __eq__(self, other):
        return isinstance(other, self.cls)


class IsHttpRequest(IsA):
    """Class to compare param is django.http.HttpRequest."""
    def __init__(self):
        super(IsHttpRequest, self).__init__(http.HttpRequest)
