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

INDEX_TEMPLATE = 'admin/hosts/index.html'
INDEX_URL = reverse('horizon:admin:hosts:index')
DETAIL_TEMPLATE = 'admin/hosts/detail.html'
DETAIL_URL_BASE = 'horizon:admin:hosts:detail'


class HostsTests(test.BaseAdminViewTests):
    @test.create_stubs({api.client: ('host_list',)})
    def test_index(self):
        hosts = self.hosts.list()
        api.client.host_list(IsA(http.HttpRequest)).AndReturn(hosts)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'compute-2')

    @test.create_stubs({api.client: ('host_list',)})
    def test_index_no_hosts(self):
        api.client.host_list(IsA(http.HttpRequest)).AndReturn(())
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @test.create_stubs({api.client: ('host_list',)})
    def test_index_error(self):
        api.client.host_list(
            IsA(http.HttpRequest)
        ).AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    @test.create_stubs({api.client: ('host_get',)})
    def test_host_detail(self):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        api.client.host_get(IsA(http.HttpRequest),
                            host['id']).AndReturn(host)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[host['id']]))
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'ex1')

    @test.create_stubs({api.client: ('host_get',)})
    def test_host_detail_error(self):
        api.client.host_get(IsA(http.HttpRequest),
                            'invalid').AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)
