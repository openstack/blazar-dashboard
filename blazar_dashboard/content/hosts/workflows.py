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

import logging

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import workflows
from openstack_dashboard import api

from blazar_dashboard import api as blazar_api

LOG = logging.getLogger(__name__)


class SelectHostsAction(workflows.MembershipAction):
    def __init__(self, request, *args, **kwargs):
        super(SelectHostsAction, self).__init__(request, *args, **kwargs)
        err_msg = _('Unable to get the available hosts')

        default_role_field_name = self.get_default_role_field_name()
        self.fields[default_role_field_name] = forms.CharField(required=False)
        self.fields[default_role_field_name].initial = 'member'

        field_name = self.get_member_field_name('member')
        self.fields[field_name] = forms.MultipleChoiceField(required=False)

        try:
            nova_hosts = api.nova.host_list(request)
            blazar_hosts = blazar_api.client.host_list(request)
        except Exception:
            exceptions.handle(request, err_msg)

        nova_hostnames = []
        for host in nova_hosts:
            if (host.host_name not in nova_hostnames
                    and host.service == u'compute'):
                nova_hostnames.append(host.host_name)

        blazar_hostnames = []
        for host in blazar_hosts:
            if host.hypervisor_hostname not in blazar_hostnames:
                blazar_hostnames.append(host.hypervisor_hostname)

        host_names = list(set(nova_hostnames) - set(blazar_hostnames))
        host_names.sort()

        self.fields[field_name].choices = \
            [(host_name, host_name) for host_name in host_names]

        self.fields[field_name].initial = None

    class Meta(object):
        name = _("Select Hosts")
        slug = "select_hosts"


class AddExtraCapsAction(workflows.Action):
    extra_caps = forms.CharField(
        label=_("Extra Capabilities"),
        required=False,
        help_text=_('Enter extra capabilities of hosts in JSON'),
        widget=forms.Textarea(
            attrs={'rows': 5}),
        max_length=511)

    class Meta(object):
        name = _("Extra Capabilities")
        slug = "add_extra_caps"

    def clean(self):
        cleaned_data = super(AddExtraCapsAction, self).clean()
        extra_caps = cleaned_data.get('extra_caps')

        if extra_caps:
            try:
                extra_caps = eval(extra_caps)
                cleaned_data['extra_caps'] = extra_caps
            except (SyntaxError, NameError):
                raise forms.ValidationError(
                    _('Extra capabilities must written in JSON')
                )

        return cleaned_data


class SelectHostsStep(workflows.UpdateMembersStep):
    action_class = SelectHostsAction
    help_text = _("Select hosts to create")
    available_list_title = _("All available hosts")
    members_list_title = _("Selected hosts")
    no_available_text = _("No host found.")
    no_members_text = _("No host selected.")
    show_roles = False
    contributes = ("names",)

    def contribute(self, data, context):
        if data:
            member_field_name = self.get_member_field_name('member')
            context['names'] = data.get(member_field_name, [])
        return context


class AddExtraCapsStep(workflows.Step):
    action_class = AddExtraCapsAction
    help_text = _("Add extra capabilities")
    show_roles = False
    contributes = ("extra_caps",)

    def contribute(self, data, context):
        context['extra_caps'] = data.get('extra_caps')
        return context


class CreateHostsWorkflow(workflows.Workflow):
    slug = "create_hosts"
    name = _("Create Hosts")
    finalize_button_name = _("Create Hosts")
    success_url = 'horizon:admin:hosts:index'
    default_steps = (SelectHostsStep, AddExtraCapsStep)

    def handle(self, request, context):
        try:
            for name in context['names']:
                if context['extra_caps']:
                    blazar_api.client.host_create(request, name=name,
                                                  **context['extra_caps'])
                else:
                    blazar_api.client.host_create(request, name=name)
                messages.success(request, _('Host %s was successfully '
                                            'created.') % name)
        except Exception:
            exceptions.handle(request, _('Unable to create host.'))
            return False

        return True
