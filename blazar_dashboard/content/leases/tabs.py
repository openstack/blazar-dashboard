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
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tabs

from blazar_dashboard.api import client

RESERVATION_GENERALS = (
    'id',
    'lease_id',
    'resource_id',
    'resource_type',
    'status',
    'missing_resources',
    'resources_changed',
    'created_at',
    'updated_at'
)


class OverviewTab(tabs.Tab):
    name = _("Overview")
    slug = "overview"
    template_name = "project/leases/_detail_overview.html"

    def get_context_data(self, request):
        lease_id = self.tab_group.kwargs['lease_id']
        try:
            lease = client.lease_get(self.request, lease_id)
        except Exception:
            redirect = reverse('horizon:project:leases:index')
            msg = _('Unable to retrieve lease details.')
            exceptions.handle(request, msg, redirect=redirect)

        return {'lease': lease,
                'reservation_generals': RESERVATION_GENERALS}


class LeaseDetailTabs(tabs.TabGroup):
    slug = "lease_details"
    tabs = (OverviewTab,)
