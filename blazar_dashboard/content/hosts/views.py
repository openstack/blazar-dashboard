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

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from horizon import tabs
from horizon import workflows

from blazar_dashboard import api
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
