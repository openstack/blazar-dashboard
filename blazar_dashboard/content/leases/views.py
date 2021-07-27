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

from blazar_dashboard import api
from blazar_dashboard.content.leases import tables as project_tables
from blazar_dashboard.content.leases import tabs as project_tabs
from blazar_dashboard.content.leases import workflows as project_workflows
from django.http import JsonResponse
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon import views
from horizon import workflows
from horizon.utils import memoized


class IndexView(tables.DataTableView):
    table_class = project_tables.LeasesTable
    template_name = 'project/leases/index.html'

    def get_data(self):
        try:
            leases = api.client.lease_list(self.request)
        except Exception:
            leases = []
            msg = _('Unable to retrieve lease information.')
            exceptions.handle(self.request, msg)
        return leases


class CalendarView(views.APIView):
    template_name = 'project/leases/calendar.html'

    titles = {
        "host": _("Host Calendar"),
        "network": _("Network Calendar"),
        "device": _("Device Calendar"),
    }

    def get_data(self, request, context, *args, **kwargs):
        context["calendar_title"] = self.titles[context["resource_type"]]
        return context


def calendar_data_view(request, resource_type):
    api_mapping = {
        "host": api.client.reservation_calendar,
        "network": api.client.network_reservation_calendar,
        "device": api.client.device_reservation_calendar
    }
    data = {}
    data["project_id"] = request.user.project_id
    resources, reservations = api_mapping[resource_type](request)
    data['resources'] = resources
    data['reservations'] = reservations
    # Code for including authorized_projects capability in response
    if resource_type == "device":
        for device in resources:
            full_device = api.client.device_with_capabilities(request, device["id"])
            del device["id"]
            if "authorized_projects" in full_device:
                device["authorized_projects"] = full_device["authorized_projects"]
    return JsonResponse(data)


def extra_capabilities(request, resource_type):
    extra_capabilities = None
    if resource_type == 'computehost':
        extra_capabilities = api.client.computehost_extra_capabilities(
            request)
    elif resource_type == 'network':
        extra_capabilities = api.client.network_extra_capabilities(
            request)
    elif resource_type == 'device':
        extra_capabilities = api.client.device_extra_capabilities(
            request)
    data = {
        'extra_capabilities': extra_capabilities}
    return JsonResponse(data)


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.LeaseDetailTabs
    template_name = 'project/leases/detail.html'


class CreateView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateLease


class UpdateView(workflows.WorkflowView):
    workflow_class = project_workflows.UpdateLease

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()
        initial['lease'] = self.get_object()

        return initial

    @memoized.memoized_method
    def get_object(self):
        lease_id = self.kwargs['lease_id']
        try:
            lease = api.client.lease_get(self.request, lease_id)
        except Exception:
            msg = _("Unable to retrieve lease.")
            redirect = reverse('horizon:project:leases:index')
            exceptions.handle(self.request, msg, redirect=redirect)
        return lease
