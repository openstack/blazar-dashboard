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

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import workflows

from blazar_dashboard import api
from blazar_dashboard.content.hosts import forms as project_forms
from blazar_dashboard.content.hosts import tables as project_tables
from blazar_dashboard.content.hosts import tabs as project_tabs
from blazar_dashboard.content.hosts import workflows as project_workflows


class IndexView(tables.DataTableView):
    table_class = project_tables.HostsTable
    template_name = 'admin/hosts/index.html'

    def get_data(self):
        try:
            hosts = api.client.host_list(self.request)
        except Exception:
            hosts = []
            msg = _('Unable to retrieve host information.')
            exceptions.handle(self.request, msg)
        return hosts


class DetailView(tabs.TabView):
    tab_group_class = project_tabs.HostDetailTabs
    template_name = 'admin/hosts/detail.html'


class CreateView(workflows.WorkflowView):
    workflow_class = project_workflows.CreateHostsWorkflow
    template_name = 'admin/hosts/create.html'
    page_title = _("Create Hosts")


class UpdateView(forms.ModalFormView):
    form_class = project_forms.UpdateForm
    template_name = 'admin/hosts/update.html'
    success_url = reverse_lazy('horizon:admin:hosts:index')
    modal_header = _("Update Host")

    def get_initial(self):
        initial = super(UpdateView, self).get_initial()

        initial['host'] = self.get_object()
        if initial['host']:
            initial['host_id'] = initial['host'].id
            initial['name'] = initial['host'].hypervisor_hostname

        return initial

    def get_context_data(self, **kwargs):
        context = super(UpdateView, self).get_context_data(**kwargs)
        context['host'] = self.get_object()
        return context

    @memoized.memoized_method
    def get_object(self):
        host_id = self.kwargs['host_id']
        try:
            host = api.client.host_get(self.request, host_id)
        except Exception:
            msg = _("Unable to retrieve host.")
            redirect = reverse_lazy('horizon:admin:hosts:index')
            exceptions.handle(self.request, msg, redirect=redirect)
        return host
