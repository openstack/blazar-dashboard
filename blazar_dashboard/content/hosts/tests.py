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

from unittest import mock

from django.urls import reverse
from openstack_dashboard import api

from blazar_dashboard import api as blazar_api
from blazar_dashboard.test import helpers as test

import logging
LOG = logging.getLogger(__name__)

INDEX_TEMPLATE = 'admin/hosts/index.html'
INDEX_URL = reverse('horizon:admin:hosts:index')
DETAIL_TEMPLATE = 'admin/hosts/detail.html'
DETAIL_URL_BASE = 'horizon:admin:hosts:detail'
CREATE_URL = reverse('horizon:admin:hosts:create')
CREATE_TEMPLATE = 'admin/hosts/create.html'
UPDATE_URL_BASE = 'horizon:admin:hosts:update'
UPDATE_TEMPLATE = 'admin/hosts/update.html'


class HostsTests(test.BaseAdminViewTests):
    @mock.patch.object(blazar_api.client, 'host_list')
    def test_index(self, host_list):
        hosts = self.hosts.list()
        host_list.return_value = hosts

        res = self.client.get(INDEX_URL)

        host_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'compute-2')

    @mock.patch.object(blazar_api.client, 'host_list')
    def test_index_no_hosts(self, host_list):
        hosts = []
        host_list.return_value = hosts

        res = self.client.get(INDEX_URL)

        host_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @mock.patch.object(blazar_api.client, 'host_list')
    def test_index_error(self, host_list):
        host_list.side_effect = self.exceptions.blazar

        res = self.client.get(INDEX_URL)

        host_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    @mock.patch.object(blazar_api.client, 'host_get')
    def test_host_detail(self, host_get):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        host_get.return_value = host

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[host['id']]))

        host_get.assert_called_once_with(test.IsHttpRequest(), host['id'])
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'ex1')

    @mock.patch.object(blazar_api.client, 'host_get')
    def test_host_detail_error(self, host_get):
        host_get.side_effect = self.exceptions.blazar

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))

        host_get.assert_called_once_with(test.IsHttpRequest(), 'invalid')
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(blazar_api.client, 'host_list')
    @mock.patch.object(blazar_api.client, 'host_create')
    @mock.patch.object(api.nova, 'hypervisor_list')
    def test_create_hosts(self, hypervisor_list, host_create, host_list):
        hv_hostnames = [hv.hypervisor_hostname
                        for hv in self.hypervisors.list()]
        calls = []
        for host_name in hv_hostnames:
            calls.append(mock.call(test.IsHttpRequest(), name=host_name))
        form_data = {
            'select_hosts_role_member': hv_hostnames
        }
        host_list.return_value = []
        host_create.return_value = []
        hypervisor_list.return_value = self.hypervisors.list()

        res = self.client.post(CREATE_URL, form_data)
        host_list.assert_called_once_with(test.IsHttpRequest())
        host_create.assert_has_calls(calls)
        self.assertEqual(len(hv_hostnames), host_create.call_count)
        hypervisor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=(len(hv_hostnames) + 1))
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(blazar_api.client, 'host_list')
    @mock.patch.object(blazar_api.client, 'host_create')
    @mock.patch.object(api.nova, 'hypervisor_list')
    def test_create_hosts_with_extra_caps(self, hypervisor_list, host_create,
                                          host_list):
        hv_hostnames = [hv.hypervisor_hostname
                        for hv in self.hypervisors.list()]
        calls = []
        for host_name in hv_hostnames:
            calls.append(mock.call(test.IsHttpRequest(),
                                   name=host_name, extracap="strong"))
        form_data = {
            'select_hosts_role_member': hv_hostnames,
            'extra_caps': '{"extracap": "strong"}'
        }
        host_list.return_value = []
        host_create.return_value = []
        hypervisor_list.return_value = self.hypervisors.list()

        res = self.client.post(CREATE_URL, form_data)

        host_list.assert_called_once_with(test.IsHttpRequest())
        host_create.assert_has_calls(calls)
        self.assertEqual(len(hv_hostnames), host_create.call_count)
        hypervisor_list.assert_called_once_with(test.IsHttpRequest())
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=(len(hv_hostnames) + 1))
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(blazar_api.client, 'host_get')
    @mock.patch.object(blazar_api.client, 'host_update')
    def test_update_host(self, host_update, host_get):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        form_data = {
            'host_id': host['id'],
            'values': '{"key": "updated"}'
        }
        host_get.return_value = host
        host_update.return_value = []

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[host['id']]),
                               form_data)

        host_get.assert_called_once_with(test.IsHttpRequest(), host['id'])
        host_update.assert_called_once_with(test.IsHttpRequest(),
                                            host_id=host['id'],
                                            values={"key": "updated"})
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(blazar_api.client, 'host_get')
    @mock.patch.object(blazar_api.client, 'host_update')
    def test_update_host_error(self, host_update, host_get):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        form_data = {
            'host_id': host['id'],
            'values': '{"key": "updated"}'
        }
        host_get.return_value = host
        host_update.side_effect = self.exceptions.blazar

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[host['id']]),
                               form_data)

        host_get.assert_called_once_with(test.IsHttpRequest(), host['id'])
        host_update.assert_called_once_with(test.IsHttpRequest(),
                                            host_id=host['id'],
                                            values={"key": "updated"})
        self.assertNoFormErrors(res)
        self.assertContains(res, 'An error occurred while updating')

    @mock.patch.object(blazar_api.client, 'host_list')
    @mock.patch.object(blazar_api.client, 'host_delete')
    def test_delete_host(self, host_delete, host_list):
        hosts = self.hosts.list()
        host = self.hosts.get(hypervisor_hostname='compute-1')
        action = 'hosts__delete__%s' % host['id']
        form_data = {'action': action}
        host_list.return_value = hosts

        res = self.client.post(INDEX_URL, form_data)

        host_list.assert_called_once_with(test.IsHttpRequest())
        host_delete.assert_called_once_with(test.IsHttpRequest(), host['id'])
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(blazar_api.client, 'host_list')
    @mock.patch.object(blazar_api.client, 'host_delete')
    def test_delete_host_error(self, host_delete, host_list):
        hosts = self.hosts.list()
        host = self.hosts.get(hypervisor_hostname='compute-1')
        action = 'hosts__delete__%s' % host['id']
        form_data = {'action': action}
        host_list.return_value = hosts
        host_delete.side_effect = self.exceptions.blazar

        res = self.client.post(INDEX_URL, form_data)

        host_list.assert_called_once_with(test.IsHttpRequest())
        host_delete.assert_called_once_with(test.IsHttpRequest(), host['id'])
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)
