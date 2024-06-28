# Copyright 2014 Intel Corporation
# All Rights Reserved.
#
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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from horizon import exceptions
from horizon import tabs

from blazar_dashboard.api import client


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = "admin/hosts/_detail_overview.html"

    def get_context_data(self, request):
        host_id = self.tab_group.kwargs['host_id']
        try:
            host = client.host_get(self.request, host_id)
        except Exception:
            redirect = reverse('horizon:admin:hosts:index')
            msg = _('Unable to retrieve host details.')
            exceptions.handle(request, msg, redirect=redirect)

        return {'host': host}


class HostDetailTabs(tabs.TabGroup):
    slug = "host_details"
    tabs = (OverviewTab,)
