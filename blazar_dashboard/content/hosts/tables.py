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

from django.template import defaultfilters as filters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import tables
from horizon.templatetags import sizeformat

from blazar_dashboard import api


class CreateHosts(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Hosts")
    url = "horizon:admin:hosts:create"
    classes = ("ajax-modal",)
    icon = "plus"


class UpdateHost(tables.LinkAction):
    name = "update"
    verbose_name = _("Update Host")
    url = "horizon:admin:hosts:update"
    classes = ("btn-create", "ajax-modal")


class DeleteHost(tables.DeleteAction):
    name = "delete"
    data_type_singular = _("Host")
    data_type_plural = _("Hosts")
    classes = ('btn-danger', 'btn-terminate')

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Host",
            u"Delete Hosts",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Host",
            u"Deleted Hosts",
            count
        )

    def delete(self, request, host_id):
        api.client.host_delete(request, host_id)


class HostsTable(tables.DataTable):
    name = tables.Column("hypervisor_hostname", verbose_name=_("Host name"),
                         link="horizon:admin:hosts:detail")
    vcpus = tables.Column("vcpus", verbose_name=_("VCPUs"))
    memory_mb = tables.Column("memory_mb", verbose_name=_("RAM"),
                              filters=(sizeformat.mb_float_format,))
    local_gb = tables.Column("local_gb", verbose_name=_("Local Storage"),
                             filters=(sizeformat.diskgbformat,))
    type = tables.Column("hypervisor_type", verbose_name=_("Hypervisor type"))
    reservable = tables.Column("reservable", verbose_name=_("Reservable"),
                               filters=(filters.yesno, filters.capfirst))

    class Meta(object):
        name = "hosts"
        verbose_name = _("Hosts")
        table_actions = (CreateHosts, DeleteHost,)
        row_actions = (UpdateHost, DeleteHost,)
