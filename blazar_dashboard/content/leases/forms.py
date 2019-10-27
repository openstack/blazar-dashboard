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

import datetime
import json
import logging
import re

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages
import pytz

from blazar_dashboard import api
from blazar_dashboard import conf
from . import widgets

LOG = logging.getLogger(__name__)


class CreateForm(forms.SelfHandlingForm):
    # General fields
    name = forms.CharField(
        label=_("Lease Name"),
        max_length=80,
        required=True
    )

    start_date = forms.DateTimeField(
        label=_("Start Date"),
        required=False,
        help_text=_('Enter date with the format YYYY-MM-DD or leave blank for today'),
        error_messages={
            'invalid': _('Value should be date, formatted YYYY-MM-DD'),
        },
        input_formats=['%Y-%m-%d'],
        widget=forms.DateTimeInput(
            attrs={'placeholder':'Today', 'class':'datepicker','autocomplete':'off'}),
    )
    start_time = forms.DateTimeField(
        label=_('Start Time'),
        help_text=_('Enter time with the format HH:MM (24-hour clock) or leave blank for now'),
        error_messages={
            'invalid': _('Value should be time, formatted HH:MM (24-hour clock)'),
        },
        input_formats=['%H:%M'],
        widget=forms.DateTimeInput(attrs={'placeholder':'Now','autocomplete':'off'}),
        required=False,
    )
    number_of_days = forms.IntegerField(
        label=_("Lease Length (days)"),
        required=False,
        help_text=_('Set to zero to schedule leases that start and end on the same day'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput()
    )
    end_date = forms.DateTimeField(
        label=_("Ends"),
        required=False,
        help_text=_('Date is calculated from the start date and duration.'),
        error_messages={
            'invalid': _('Value should be date, formatted YYYY-MM-DD'),
        },
        input_formats=['%Y-%m-%d'],
        widget=forms.DateTimeInput(
            attrs={'placeholder':'Tomorrow', 'class':'datepicker'}),
    )
    end_time = forms.DateTimeField(
        label=_('End Time'),
        help_text=_('Enter time with the format HH:MM (24-hour clock) or leave blank for same time as now'),
        error_messages={
            'invalid': _('Value should be time, formatted HH:MM (24-hour clock)'),
        },
        input_formats=['%H:%M'],
        widget=forms.DateTimeInput(attrs={'placeholder':'Same time as now'}),
        required=False,
    )

    resource_type_host = forms.BooleanField(
        label=_("Reserve Physical Host"),
        initial = True,
        required = False,
        widget=forms.CheckboxInput(attrs={
            'data-slug': 'source'})
    )

    resource_type_network = forms.BooleanField(
        label=_("Reserve Network"),
        required=False,
    )

    # Fields for host reservation
    min_hosts = forms.IntegerField(
        label=_('Minimum Number of Hosts'),
        required=False,
        help_text=_('Enter the minimum number of hosts to reserve.'),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Minimum Number of Hosts')})
    )
    max_hosts = forms.IntegerField(
        label=_('Maximum Number of Hosts'),
        required=False,
        help_text=_('Enter the maximum number of hosts to reserve.'),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Maximum Number of Hosts')})
    )
    resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Resource Properties')})
    )

    # Fields for network reservation
    network_name = forms.CharField(
        label=_('Network Name'),
        required=False,
        help_text=_('Name to use when creating the Neutron network.'),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-network': _('Network Name')})
    )
    network_description = forms.CharField(
        label=_('Network Description'),
        required=False,
        help_text=_('Description to use when creating the Neutron network.'),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-network': _('Network Description')})
    )
    network_ip_count = forms.IntegerField(
        label=_('Number of Floating IP Addresses Needed'),
        required=False,
        help_text=_('If needed, enter the number of Floating IP addresses you would like to reserve.'),
        min_value=0,
        initial=0,
        widget=forms.NumberInput()
    )

    resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Resource Properties')})
    )
    affinity = forms.ChoiceField(
        label=_("Affinity Rule"),
        required=False,
        choices=(
            (None, _('None')),
            (True, _('Affinity')),
            (False, _('Anti-Affinity')),
        ),
        initial=None,
        widget=forms.ThemableSelectWidget(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-instance': _('Affinity Rule')})
    )

    def handle(self, request, data):
        reservations = []
        if data['resource_type_host'] == True:
            # these resource properties only apply to host reservations
            res_props = data['resource_properties']
            reservations.append(
                {
                    'resource_type': 'physical:host',
                    'min': data['min_hosts'],
                    'max': data['max_hosts'],
                    'hypervisor_properties': '',
                    'resource_properties': res_props if res_props else '',
                })
        if data['network_ip_count'] > 0:
            network_id = conf.floatingip_reservation.get('network_id')
            reservations.append(
                {
                    'resource_type': 'virtual:floatingip',
                    'network_id': network_id,
                    'amount': data['network_ip_count'],
                }
            )
        if data['resource_type_network'] == True:
            reservations.append(
                {
                    'resource_type': 'network',
                    'network_name': data['network_name'],
                    'network_description': data['network_description'],
                    'network_properties': '',
                    'resource_properties': '',
                })


        events = []
        try:
            lease = api.client.lease_create(
                request, data['name'],
                data['start_date'].strftime('%Y-%m-%d %H:%M'),
                data['end_date'].strftime('%Y-%m-%d %H:%M'),
                reservations, events)
            # store created_lease_id in session for redirect in view
            request.session['created_lease_id'] = lease.id
            messages.success(request, _('Lease %s was successfully '
                                        'created.') % data['name'])
            return True
        except Exception as e:
            LOG.error('Error submitting lease: %s', e)
            exceptions.handle(request,
                              message='An error occurred while creating this '
                                      'lease: %s. Please try again.' % e)

    def clean(self):

        cleaned_data = super(CreateForm, self).clean()
        localtz = pytz.timezone(self.request.session.get(
            'django_timezone',
            self.request.COOKIES.get('django_timezone', 'UTC')))
        if not (cleaned_data['resource_type_host'] or cleaned_data['resource_type_network']):
             raise forms.ValidationError("Please select a resource type.")

        if cleaned_data['resource_type_network'] and not cleaned_data['network_name']:
            raise forms.ValidationError("Please enter all network details.")

        ##### straight copy
        # convert dates and times to datetime UTC
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")

        if start_date == '' or start_date == None:
            start_date = datetime.datetime.now(localtz) + datetime.timedelta(minutes=1)

        if start_time == '' or start_time == None:
            start_time = datetime.datetime.now(localtz) + datetime.timedelta(minutes=1)


        start_datetime = self.prepare_datetimes(start_date, start_time)

        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")

        if end_date == '' or end_date == None:
            end_date = datetime.datetime.now(localtz) + datetime.timedelta(days=1)

        if end_time == '' or end_time == None:
            end_time = datetime.datetime.now(localtz) + datetime.timedelta(days=1)


        end_datetime = self.prepare_datetimes(end_date, end_time)
        ##### plugging results
        cleaned_data['start_date'] = start_datetime
        cleaned_data['end_date'] = end_datetime
        ##### end copy

        if cleaned_data['start_date'] < datetime.datetime.now(tz=pytz.utc):
            raise forms.ValidationError("Start date must be in the future")

        if cleaned_data['start_date'] >= cleaned_data['end_date']:
            raise forms.ValidationError("Start date must be before end")

        # precheck for name conflicts
        leases = api.client.lease_list(self.request)
        if cleaned_data['name'] in {lease['name'] for lease in leases}:
            raise forms.ValidationError("A lease with this name already exists.")

        # precheck for host availability
        num_hosts = api.client.compute_host_available(self.request,
                                                      cleaned_data['start_date'],
                                                      cleaned_data['end_date'])
        if (cleaned_data['resource_type_host'] and
            cleaned_data['min_hosts'] > num_hosts):
            raise forms.ValidationError(_(
                "Not enough hosts are available for this reservation (minimum "
                "%s requested; %s available). Try adjusting the number of "
                "hosts requested or the date range for the reservation.")
                % (cleaned_data['min_hosts'], num_hosts))

        return cleaned_data

    def prepare_datetimes(self, date_val, time_val):
        """
        Ensure the date and time are in user's timezone, then convert to UTC.
        """
        localtz = pytz.timezone(self.request.session.get('django_timezone', self.request.COOKIES.get('django_timezone', 'UTC')))
        datetime_val = date_val.replace(hour=time_val.time().hour, minute=time_val.time().minute, tzinfo=None)
        datetime_val = localtz.localize(datetime_val)
        return datetime_val.astimezone(pytz.utc)


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
