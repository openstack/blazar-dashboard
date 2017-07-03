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

from django.core.urlresolvers import reverse
from django import http
from mox3.mox import IsA

from blazar_dashboard import api
from blazar_dashboard.test import helpers as test

import logging
LOG = logging.getLogger(__name__)

INDEX_TEMPLATE = 'project/leases/index.html'
INDEX_URL = reverse('horizon:project:leases:index')
DETAIL_TEMPLATE = 'project/leases/detail.html'
DETAIL_URL_BASE = 'horizon:project:leases:detail'
UPDATE_URL_BASE = 'horizon:project:leases:update'
UPDATE_TEMPLATE = 'project/leases/update.html'


class LeasesTests(test.TestCase):
    @test.create_stubs({api.client: ('lease_list',)})
    def test_index(self):
        leases = self.leases.list()
        api.client.lease_list(IsA(http.HttpRequest)).AndReturn(leases)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'lease-2')
        self.assertContains(res, 'lease-1')

    @test.create_stubs({api.client: ('lease_list',)})
    def test_index_no_leases(self):
        api.client.lease_list(IsA(http.HttpRequest)).AndReturn(())
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @test.create_stubs({api.client: ('lease_list',)})
    def test_index_error(self):
        api.client.lease_list(
            IsA(http.HttpRequest)
        ).AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    def test_lease_actions(self):
        pass

    @test.create_stubs({api.client: ('lease_get',)})
    def test_lease_detail(self):
        lease = self.leases.get(name='lease-1')
        api.client.lease_get(IsA(http.HttpRequest),
                             lease['id']).AndReturn(lease)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[lease['id']]))
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'lease-1')

    @test.create_stubs({api.client: ('lease_get',)})
    def test_lease_detail_error(self):
        api.client.lease_get(IsA(http.HttpRequest),
                             'invalid').AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.client: ('lease_get', 'lease_update')})
    def test_update_lease(self):
        lease = self.leases.get(name='lease-1')
        api.client.lease_get(
            IsA(http.HttpRequest),
            lease['id']
        ).AndReturn(lease)
        api.client.lease_update(
            IsA(http.HttpRequest),
            lease_id=lease['id'],
            name='newname',
            prolong_for='1h'
        )
        form_data = {
            'lease_id': lease['id'],
            'lease_name': 'newname',
            'end_time': '+1h'
        }
        self.mox.ReplayAll()

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.client: ('lease_get', 'lease_update')})
    def test_update_lease_error(self):
        lease = self.leases.get(name='lease-1')
        api.client.lease_get(
            IsA(http.HttpRequest),
            lease['id']
        ).AndReturn(lease)
        api.client.lease_update(
            IsA(http.HttpRequest),
            lease_id=lease['id'],
            name='newname',
            prolong_for='1h'
        ).AndRaise(self.exceptions.blazar)
        form_data = {
            'lease_id': lease['id'],
            'lease_name': 'newname',
            'end_time': '+1h'
        }
        self.mox.ReplayAll()

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[lease['id']]),
                               form_data)
        self.assertTemplateUsed(UPDATE_TEMPLATE)
        self.assertNoFormErrors(res)
        self.assertContains(res, 'An error occurred while updating')

    @test.create_stubs({api.client: ('lease_list', 'lease_delete')})
    def test_delete_lease(self):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        api.client.lease_list(IsA(http.HttpRequest)).AndReturn(leases)
        api.client.lease_delete(IsA(http.HttpRequest), lease['id'])
        self.mox.ReplayAll()

        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        res = self.client.post(INDEX_URL, form_data)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({api.client: ('lease_list', 'lease_delete')})
    def test_delete_lease_error(self):
        leases = self.leases.list()
        lease = self.leases.get(name='lease-1')
        api.client.lease_list(IsA(http.HttpRequest)).AndReturn(leases)
        api.client.lease_delete(IsA(http.HttpRequest),
                                lease['id']).AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        action = 'leases__delete__%s' % lease['id']
        form_data = {'action': action}
        res = self.client.post(INDEX_URL, form_data)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)
