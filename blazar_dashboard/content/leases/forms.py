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

import logging

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages

from blazar_dashboard import api

LOG = logging.getLogger(__name__)


class UpdateForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Update Lease Parameters')

    lease_id = forms.CharField(
        label=_('Lease ID'), widget=forms.widgets.HiddenInput, required=True)
    lease_name = forms.CharField(
        label=_('Lease name'), widget=forms.TextInput(), required=False)
    start_time = forms.CharField(
        label=_('Start time'),
        widget=forms.TextInput(
            attrs={'placeholder': _('Valid suffix are d/h/m (e.g. +1h)')}),
        required=False)
    end_time = forms.CharField(
        label=_('End time'),
        widget=forms.TextInput(
            attrs={'placeholder': _('Valid suffix are d/h/m (e.g. +1h)')}),
        required=False)

    def handle(self, request, data):
        lease_id = data.get('lease_id')

        fields = {}

        lease_name = data.get('lease_name', None)
        if lease_name:
            fields['name'] = lease_name

        start_time = data.get('start_time', None)
        end_time = data.get('end_time', None)
        if start_time:
            if start_time[0] == '+':
                fields['defer_by'] = start_time[1:]
            elif start_time[0] == '-':
                fields['advance_by'] = start_time[1:]
        if end_time:
            if end_time[0] == '+':
                fields['prolong_for'] = end_time[1:]
            elif end_time[0] == '-':
                fields['reduce_by'] = end_time[1:]

        try:
            api.client.lease_update(self.request, lease_id=lease_id, **fields)
            messages.success(request, _("Lease update started."))
            return True
        except Exception as e:
            LOG.error('Error updating lease: %s', e)
            exceptions.handle(request,
                              message="An error occurred while updating this"
                                      " lease: %s. Please try again." % e)

    def clean(self):
        cleaned_data = super(UpdateForm, self).clean()

        lease_name = cleaned_data.get("lease_name")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if not (lease_name or start_time or end_time):
            raise forms.ValidationError("Nothing to update.")
