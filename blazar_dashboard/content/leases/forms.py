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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages
import json
import logging

from . import widgets


LOG = logging.getLogger(__name__)


class UpdateForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Update Lease Parameters')

    lease_id = forms.CharField(
        label=_('Lease ID'), widget=forms.widgets.HiddenInput, required=True)
    lease_name = forms.CharField(
        label=_('Lease name'), widget=forms.TextInput(), required=False)
    prolong_for = forms.CharField(
        label=_('Prolong for'),
        widget=widgets.TimespanWidget(),
        required=False)
    reduce_by = forms.CharField(
        label=_('Reduce by'),
        widget=widgets.TimespanWidget(),
        required=False)
    reservations = forms.CharField(
        label=_("Reservation values to update"),
        help_text=_('Enter reservation values to update as JSON'),
        widget=forms.Textarea(
            attrs={'rows': 8,
                   'placeholder':
                   'e.g.\n'
                   '[\n'
                   '    {\n'
                   '        "id": "087bc740-6d2d-410b-9d47-c7b2b55a9d36",\n'
                   '        "max": 3\n'
                   '    }\n'
                   ']'}),
        max_length=511,
        required=False)
    # Fields for host reservation
    min_hosts = forms.IntegerField(
        label=_('Minimum Number of Hosts'),
        required=False,
        help_text=_('Enter the updated minimum number of hosts to reserve.'),
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Minimum Number of Hosts')})
    )
    max_hosts = forms.IntegerField(
        label=_('Maximum Number of Hosts'),
        required=False,
        help_text=_('Enter the updated maximum number of hosts to reserve.'),
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Maximum Number of Hosts')})
    )

    def __init__(self, request, *args, **kwargs):
        super(UpdateForm, self).__init__(request, *args, **kwargs)
        resource_types = []
        for reservation in kwargs['initial']['lease'].reservations:
            resource_types.append(reservation['resource_type'])
        if not 'physical:host' in resource_types:
            del self.fields['min_hosts']
            del self.fields['max_hosts']
        return

    def handle(self, request, data):
        lease_id = data.get('lease_id')

        fields = {}

        lease_name = data.get('lease_name', None)
        if lease_name:
            fields['name'] = lease_name

        # TODO(nicktimko): Create a better widget/use more appropriate
        # controls because prolonging/reducing aren't really independent
        # choices. Also expose other fields that lease.update supports.
        # the TimespanWidget emits strings of the form "<int>s"
        try:
            prolong = float((data.get('prolong_for') or '0s').rstrip('s'))
            reduce = float((data.get('reduce_by') or '0s').rstrip('s'))
        except ValueError as e:
            logger.error('Error updating lease: %s', e)
            exceptions.handle(request, message="Invalid value provided.")
            return

        net_mins = round((prolong - reduce) / 60.0)
        min_string = '{:.0f}m'.format(abs(net_mins))
        if net_mins > 0:
            fields['prolong_for'] = min_string
        elif net_mins < 0:
            fields['reduce_by'] = min_string

        min_hosts = data.get('min_hosts')
        max_hosts = data.get('max_hosts')
        if min_hosts and max_hosts:
            try:
                min_hosts = int(data.get('min_hosts'))
                max_hosts = int(data.get('max_hosts'))
            except ValueError as e:
                logger.error('Error updating lease: %s', e)
                exceptions.handle(request, message="Invalid value provided.")
                return

            lease = api.client.lease_get(self.request, lease_id)
            fields['reservations'] = lease['reservations']
            if len(fields['reservations']) != 1:
                messages.error(request, "Cannot update node count for a lease "
                                        "with multiple reservations.")
                return
            fields['reservations'][0]['min'] = min_hosts
            fields['reservations'][0]['max'] = min_hosts

        reservations = data.get('reservations', None)
        if reservations:
            fields['reservations'] = reservations

        try:
            api.client.lease_update(self.request, lease_id=lease_id, **fields)
            messages.success(request, _("Lease update started."))
            return True
        except Exception as e:
            LOG.error('Error updating lease: %s', e)
            exceptions.handle(request,
                              message="An error occurred while updating this "
                                      "lease: %s. Please try again." % e)

    def clean(self):
        cleaned_data = super(UpdateForm, self).clean()

        lease_name = cleaned_data.get("lease_name")
        prolong_for = cleaned_data.get("prolong_for")
        reduce_by = cleaned_data.get("reduce_by")
        min_hosts = cleaned_data.get("min_hosts")
        max_hosts = cleaned_data.get("max_hosts")

        if not (lease_name or prolong_for or reduce_by or min_hosts or max_hosts):
            raise forms.ValidationError("Nothing to update.")

        if (min_hosts or max_hosts) and not (min_hosts and max_hosts):
            raise forms.ValidationError("You must provide both min_hosts and "
                                        "max_hosts.")
