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

from datetime import datetime
from datetime import timezone
from unittest import mock

from django.urls import reverse

from blazar_dashboard import api
from blazar_dashboard.test import helpers as test

import logging
LOG = logging.getLogger(__name__)

INDEX_TEMPLATE = 'project/leases/index.html'
INDEX_URL = reverse('horizon:project:leases:index')
DETAIL_TEMPLATE = 'project/leases/detail.html'
DETAIL_URL_BASE = 'horizon:project:leases:detail'
CREATE_URL = reverse('horizon:project:leases:create')
CREATE_TEMPLATE = 'project/leases/create.html'
UPDATE_URL_BASE = 'horizon:project:leases:update'
UPDATE_TEMPLATE = 'project/leases/update.html'


class LeasesTests(test.TestCase):
    @mock.patch.object(api.client, 'lease_list')
    def test_index(self, lease_list):
        leases = self.leases.list()
        lease_list.return_value = leases

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'lease-2')
        self.assertContains(res, 'lease-1')

    @mock.patch.object(api.client, 'lease_list')
    def test_index_no_leases(self, lease_list):
        leases = []
        lease_list.return_value = leases

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @mock.patch.object(api.client, 'lease_list')
    def test_index_error(self, lease_list):
        lease_list.side_effect = self.exceptions.blazar

        res = self.client.get(INDEX_URL)

        lease_list.assert_called_once_with(test.IsHttpRequest())
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    @mock.patch.object(api.client, 'lease_get')
    def test_lease_detail(self, lease_get):
        lease = self.leases.get(name='lease-1')
        lease_get.return_value = lease

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[lease['id']]))

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'lease-1')

    @mock.patch.object(api.client, 'lease_get')
    def test_lease_detail_error(self, lease_get):
        lease_get.side_effect = self.exceptions.blazar

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))

        lease_get.assert_called_once_with(test.IsHttpRequest(), 'invalid')
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_create')
    def test_create_lease_host_reservation(self, lease_create):
        start_date = datetime(2030, 6, 27, 18, 0, tzinfo=timezone.utc)
        end_date = datetime(2030, 6, 30, 18, 0, tzinfo=timezone.utc)
        new_lease = self.leases.get(name='lease-1')
        form_data = {
            'name': 'lease-1',
            'start_date': start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
            'resource_type': 'host',
            'min_hosts': 1,
            'max_hosts': 1,
            'hypervisor_properties': '[">=", "$vcpus", "2"]'
        }
        lease_create.return_value = new_lease

        res = self.client.post(CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            'lease-1',
            start_date.strftime('%Y-%m-%d %H:%M'),
            end_date.strftime('%Y-%m-%d %H:%M'),
            [
                {
                    'min': 1,
                    'max': 1,
                    'hypervisor_properties': '[">=", "$vcpus", "2"]',
                    'resource_properties': '',
                    'resource_type': 'physical:host',
                }
            ],
            [])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_create')
    def test_create_lease_instance_reservation(self, lease_create):
        start_date = datetime(2030, 6, 27, 18, 0, tzinfo=timezone.utc)
        end_date = datetime(2030, 6, 30, 18, 0, tzinfo=timezone.utc)
        dummy_lease = {}
        form_data = {
            'name': 'lease-1',
            'start_date': start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
            'resource_type': 'instance',
            'amount': 3,
            'vcpus': 2,
            'memory_mb': 4096,
            'disk_gb': 128,
            'affinity': False,
            'resource_properties': '["==", "$energy", "clean"]'
        }
        lease_create.return_value = dummy_lease

        res = self.client.post(CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            'lease-1',
            start_date.strftime('%Y-%m-%d %H:%M'),
            end_date.strftime('%Y-%m-%d %H:%M'),
            [
                {
                    'resource_type': 'virtual:instance',
                    'amount': 3,
                    'vcpus': 2,
                    'memory_mb': 4096,
                    'disk_gb': 128,
                    'affinity': 'False',
                    'resource_properties': '["==", "$energy", "clean"]'
                }
            ],
            [])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_create')
    def test_create_lease_client_error(self, lease_create):
        start_date = datetime(2030, 6, 27, 18, 0, tzinfo=timezone.utc)
        end_date = datetime(2030, 6, 30, 18, 0, tzinfo=timezone.utc)
        form_data = {
            'name': 'lease-1',
            'start_date': start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M'),
            'resource_type': 'host',
            'min_hosts': 1,
            'max_hosts': 1,
        }
        lease_create.side_effect = self.exceptions.blazar

        res = self.client.post(CREATE_URL, form_data)

        lease_create.assert_called_once_with(
            test.IsHttpRequest(),
            'lease-1',
            start_date.strftime('%Y-%m-%d %H:%M'),
            end_date.strftime('%Y-%m-%d %H:%M'),
            [
                {
                    'min': 1,
                    'max': 1,
                    'hypervisor_properties': '',
                    'resource_properties': '',
                    'resource_type': 'physical:host',
                }
            ],
            [])
        self.assertTemplateUsed(res, CREATE_TEMPLATE)
        self.assertNoFormErrors(res)
        self.assertContains(res, 'An error occurred while creating')

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_name_and_date(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_id': lease['id'],
            'lease_name': 'newname',
            'end_time': '+1h'
        }
        lease_get.return_value = lease

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(test.IsHttpRequest(),
                                             lease_id=lease['id'],
                                             name='newname',
                                             prolong_for='1h')
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_reservations(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_id': lease['id'],
            'reservations': '[{"id": "087bc740-6d2d-410b-9d47-c7b2b55a9d36",'
                            ' "max": 3}]'
        }
        lease_get.return_value = lease

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(
            test.IsHttpRequest(),
            lease_id=lease['id'],
            reservations=[{
                "id": "087bc740-6d2d-410b-9d47-c7b2b55a9d36",
                "max": 3}])
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_get')
    @mock.patch.object(api.client, 'lease_update')
    def test_update_lease_error(self, lease_update, lease_get):
        lease = self.leases.get(name='lease-1')
        form_data = {
            'lease_id': lease['id'],
            'lease_name': 'newname',
            'end_time': '+1h'
        }
        lease_get.return_value = lease
        lease_update.side_effect = self.exceptions.blazar

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)

        lease_get.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        lease_update.assert_called_once_with(test.IsHttpRequest(),
                                             lease_id=lease['id'],
                                             name='newname',
                                             prolong_for='1h')
        self.assertTemplateUsed(UPDATE_TEMPLATE)
        self.assertNoFormErrors(res)
        self.assertContains(res, 'An error occurred while updating')

    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_delete')
    def test_delete_lease(self, lease_delete, lease_list):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        lease_list.return_value = leases

        res = self.client.post(INDEX_URL, form_data)

        lease_list.assert_called_once_with(test.IsHttpRequest())
        lease_delete.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @mock.patch.object(api.client, 'lease_list')
    @mock.patch.object(api.client, 'lease_delete')
    def test_delete_lease_error(self, lease_delete, lease_list):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        lease_list.return_value = leases
        lease_delete.side_effect = self.exceptions.blazar

        res = self.client.post(INDEX_URL, form_data)

        lease_list.assert_called_once_with(test.IsHttpRequest())
        lease_delete.assert_called_once_with(test.IsHttpRequest(), lease['id'])
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)
