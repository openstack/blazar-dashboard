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

from django.http import JsonResponse
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import views

from blazar_dashboard import api
from blazar_dashboard import conf
from blazar_dashboard.content.leases import forms as project_forms
from blazar_dashboard.content.leases import tables as project_tables
from blazar_dashboard.content.leases import tabs as project_tabs


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
    }

    def get_data(self, request, context, *args, **kwargs):
        if context["resource_type"] not in self.titles:
            raise exceptions.NotFound
        context["calendar_title"] = self.titles[context["resource_type"]]
        return context


def calendar_data_view(request, resource_type):
    api_mapping = {
        "host": api.client.reservation_calendar,
    }
    attribute_mapping = {
        "host": conf.host_reservation.get('calendar_attribute'),
    }
    data = {}
    if resource_type not in api_mapping:
        raise exceptions.NotFound
    resources, reservations = api_mapping[resource_type](request)
    data['resources'] = resources
    data['reservations'] = reservations
    # Which attribute to use to determine calendar rows
    data['row_attr'] = attribute_mapping[resource_type]
    return JsonResponse(data)


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.LeaseDetailTabs
    template_name = 'project/leases/detail.html'


class CreateView(forms.ModalFormView):
    form_class = project_forms.CreateForm
    template_name = 'project/leases/create.html'
    success_url = reverse_lazy('horizon:project:leases:index')
    modal_id = "create_lease_modal"
    modal_header = _("Create Lease")
    submit_label = _("Create Lease")
    submit_url = reverse_lazy('horizon:project:leases:create')


class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateForm
    template_name = 'project/leases/update.html'
    success_url = reverse_lazy('horizon:project:leases:index')
    modal_header = _("Update Lease")

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()

        initial['lease'] = self.get_object()
        if initial['lease']:
            initial['lease_id'] = initial['lease'].id
            initial['name'] = initial['lease'].name

        return initial

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['lease'] = self.get_object()
        return context

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
