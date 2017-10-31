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
from horizon import tables
from horizon.templatetags import sizeformat


class HostsTable(tables.DataTable):
    name = tables.Column("hypervisor_hostname", verbose_name=_("Host name"))
    vcpus = tables.Column("vcpus", verbose_name=_("VCPUs"))
    memory_mb = tables.Column("memory_mb", verbose_name=_("RAM"),
                              filters=(sizeformat.mb_float_format,))
    local_gb = tables.Column("local_gb", verbose_name=_("Local Storage"),
                             filters=(sizeformat.diskgbformat,))
    type = tables.Column("hypervisor_type", verbose_name=_("Hypervisor type"))

    class Meta(object):
        name = "hosts"
        verbose_name = _("Hosts")
