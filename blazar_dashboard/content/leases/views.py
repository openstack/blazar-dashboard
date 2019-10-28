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
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon import views
from horizon.utils import memoized
import pytz

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


def calendar_data_view(request):
    data = {}
    data['compute_hosts'] = api.client.compute_host_list(request)
    data['reservations'] = setUTC(api.client.reservation_calendar(request))

    return JsonResponse(data)


class NetworkCalendarView(views.APIView):
    template_name = 'project/leases/network_calendar.html'


def network_calendar_data_view(request):
    data = {}
    data['networks'] = api.client.network_list(request)
    data['reservations'] = setUTC(api.client.network_reservation_calendar(request))
    return JsonResponse(data)

def setUTC(reservations):
    for r in reservations:
        r['start_date'] = pytz.utc.localize(r.get('start_date'))
        r['end_date'] = pytz.utc.localize(r.get('end_date'))
    return reservations

def extra_capability_names(request):
    data = {
        'extra_capability_names': api.client.extra_capability_names(request),
    }
    return JsonResponse(data)


def extra_capability_values(request, name):
    data = {
        'extra_capability_values': api.client.extra_capability_values(
            request, name),
    }
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

    def get_context_data(self, **kwargs):
        context = super(CreateView, self).get_context_data(**kwargs)
        tz = pytz.timezone(self.request.session.get('django_timezone', self.request.COOKIES.get('django_timezone', 'UTC')))
        context['timezone'] = tz
        context['offset'] = int((pytz.datetime.datetime.now(tz).utcoffset().total_seconds() / 60) * -1)
        context['enable_floatingip_reservations'] = (
            conf.floatingip_reservation.get('network_id') is not None)
        return context

    # def get_success_url(self):
    #     if 'created_lease_id' in self.request.session:
    #         lease_id = self.request.session.pop('created_lease_id')
    #         return reverse('horizon:project:leases:detail', args=[lease_id])
    #
    #     return reverse('horizon:project:leases:index')


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
