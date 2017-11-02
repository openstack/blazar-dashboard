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
    @test.create_stubs({blazar_api.client: ('host_list',)})
    def test_index(self):
        hosts = self.hosts.list()
        blazar_api.client.host_list(IsA(http.HttpRequest)).AndReturn(hosts)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'compute-2')

    @test.create_stubs({blazar_api.client: ('host_list',)})
    def test_index_no_hosts(self):
        blazar_api.client.host_list(IsA(http.HttpRequest)).AndReturn(())
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertNoMessages(res)
        self.assertContains(res, 'No items to display')

    @test.create_stubs({blazar_api.client: ('host_list',)})
    def test_index_error(self):
        blazar_api.client.host_list(
            IsA(http.HttpRequest)
        ).AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(INDEX_URL)
        self.assertTemplateUsed(res, INDEX_TEMPLATE)
        self.assertMessageCount(res, error=1)

    @test.create_stubs({blazar_api.client: ('host_get',)})
    def test_host_detail(self):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        blazar_api.client.host_get(IsA(http.HttpRequest),
                                   host['id']).AndReturn(host)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=[host['id']]))
        self.assertTemplateUsed(res, DETAIL_TEMPLATE)
        self.assertContains(res, 'compute-1')
        self.assertContains(res, 'ex1')

    @test.create_stubs({blazar_api.client: ('host_get',)})
    def test_host_detail_error(self):
        blazar_api.client.host_get(IsA(http.HttpRequest),
                                   'invalid').AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        res = self.client.get(reverse(DETAIL_URL_BASE, args=['invalid']))
        self.assertTemplateNotUsed(res, DETAIL_TEMPLATE)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({blazar_api.client: ('host_list', 'host_create',),
                        api.nova: ('host_list',)})
    def test_create_hosts(self):
        blazar_api.client.host_list(IsA(http.HttpRequest)
                                    ).AndReturn([])
        api.nova.host_list(IsA(http.HttpRequest)
                           ).AndReturn(self.novahosts.list())
        host_names = [h.host_name for h in self.novahosts.list()]
        for host_name in host_names:
            blazar_api.client.host_create(
                IsA(http.HttpRequest),
                name=host_name,
            ).AndReturn([])
        self.mox.ReplayAll()
        form_data = {
            'select_hosts_role_member': host_names
        }

        res = self.client.post(CREATE_URL, form_data)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=(len(host_names) + 1))
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({blazar_api.client: ('host_list', 'host_create',),
                        api.nova: ('host_list',)})
    def test_create_hosts_with_extra_caps(self):
        blazar_api.client.host_list(IsA(http.HttpRequest)
                                    ).AndReturn([])
        api.nova.host_list(IsA(http.HttpRequest)
                           ).AndReturn(self.novahosts.list())
        host_names = [h.host_name for h in self.novahosts.list()]
        for host_name in host_names:
            blazar_api.client.host_create(
                IsA(http.HttpRequest),
                name=host_name,
                extracap="strong"
            ).AndReturn([])
        self.mox.ReplayAll()
        form_data = {
            'select_hosts_role_member': host_names,
            'extra_caps': '{"extracap": "strong"}'
        }

        res = self.client.post(CREATE_URL, form_data)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=(len(host_names) + 1))
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({blazar_api.client: ('host_get', 'host_update')})
    def test_update_host(self):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        blazar_api.client.host_get(
            IsA(http.HttpRequest),
            host['id']
        ).AndReturn(host)
        blazar_api.client.host_update(
            IsA(http.HttpRequest),
            host_id=host['id'],
            values={"key": "updated"}
        )
        form_data = {
            'host_id': host['id'],
            'values': '{"key": "updated"}'
        }
        self.mox.ReplayAll()

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[host['id']]),
                               form_data)
        self.assertNoFormErrors(res)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({blazar_api.client: ('host_get', 'host_update')})
    def test_update_host_error(self):
        host = self.hosts.get(hypervisor_hostname='compute-1')
        blazar_api.client.host_get(
            IsA(http.HttpRequest),
            host['id']
        ).AndReturn(host)
        blazar_api.client.host_update(
            IsA(http.HttpRequest),
            host_id=host['id'],
            values={"key": "updated"}
        ).AndRaise(self.exceptions.blazar)
        form_data = {
            'host_id': host['id'],
            'values': '{"key": "updated"}'
        }
        self.mox.ReplayAll()

        res = self.client.post(reverse(UPDATE_URL_BASE, args=[host['id']]),
                               form_data)
        self.assertNoFormErrors(res)
        self.assertContains(res, 'An error occurred while updating')

    @test.create_stubs({blazar_api.client: ('host_list', 'host_delete')})
    def test_delete_host(self):
        hosts = self.hosts.list()
        host = self.hosts.get(hypervisor_hostname='compute-1')
        blazar_api.client.host_list(IsA(http.HttpRequest)).AndReturn(hosts)
        blazar_api.client.host_delete(IsA(http.HttpRequest), host['id'])
        self.mox.ReplayAll()

        action = 'hosts__delete__%s' % host['id']
        form_data = {'action': action}
        res = self.client.post(INDEX_URL, form_data)
        self.assertMessageCount(success=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)

    @test.create_stubs({blazar_api.client: ('host_list', 'host_delete')})
    def test_delete_host_error(self):
        hosts = self.hosts.list()
        host = self.hosts.get(hypervisor_hostname='compute-1')
        blazar_api.client.host_list(IsA(http.HttpRequest)).AndReturn(hosts)
        blazar_api.client.host_delete(
            IsA(http.HttpRequest),
            host['id']).AndRaise(self.exceptions.blazar)
        self.mox.ReplayAll()

        action = 'hosts__delete__%s' % host['id']
        form_data = {'action': action}
        res = self.client.post(INDEX_URL, form_data)
        self.assertMessageCount(error=1)
        self.assertRedirectsNoFollow(res, INDEX_URL)
