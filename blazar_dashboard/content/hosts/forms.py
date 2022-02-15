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

import json
import logging

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages

from blazar_dashboard import api

LOG = logging.getLogger(__name__)


class UpdateForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Update Host Parameters')

    host_id = forms.CharField(
        label=_('Host ID'), widget=forms.widgets.HiddenInput, required=True)
    values = forms.CharField(
        label=_("Values to Update"),
        required=True,
        help_text=_('Enter values to update in JSON'),
        widget=forms.Textarea(
            attrs={'rows': 5}),
        max_length=511)

    def handle(self, request, data):
        try:
            api.client.host_update(self.request, host_id=data.get('host_id'),
                                   values=data.get('values'))
            messages.success(request, _("Host was successfully updated."))
            return True
        except Exception as e:
            LOG.error('Error updating host: %s', e)
            exceptions.handle(request,
                              message="An error occurred while updating this"
                                      " host: %s." % e)

    def clean(self):
        cleaned_data = super(UpdateForm, self).clean()

        values = cleaned_data.get('values')
        try:
            values = json.loads(values)
            cleaned_data['values'] = values
        except json.JSONDecodeError:
            raise forms.ValidationError(
                _('Values must be written in JSON')
            )

        return cleaned_data
