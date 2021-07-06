import datetime

import pytz

from blazar_dashboard import api
from blazar_dashboard import conf
from django import template
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import workflows
import logging

from . import widgets


LOG = logging.getLogger(__name__)


class SetGeneralAction(workflows.Action):
    name = forms.CharField(
        label=_("Lease Name"),
        max_length=80,
        required=True
    )

    start_date = forms.DateTimeField(
        label=_("Start Date"),
        required=False,
        help_text=_(
            'Enter date with the format YYYY-MM-DD or leave blank for today'),
        error_messages={
            'invalid': _('Value should be date, formatted YYYY-MM-DD'),
        },
        input_formats=['%Y-%m-%d'],
        widget=forms.DateTimeInput(
            attrs={'placeholder': 'Today',
                   'class': 'datepicker',
                   'autocomplete': 'off'}),
    )
    start_time = forms.DateTimeField(
        label=_('Start Time'),
        help_text=_(
            'Enter time with the format HH:MM (24-hour clock) or leave blank'
            'for now'),
        error_messages={
            'invalid': _('Value should be time, '
                         'formatted HH:MM (24-hour clock)'),
        },
        input_formats=['%H:%M'],
        widget=forms.DateTimeInput(
            attrs={'placeholder': 'Now', 'autocomplete': 'off'}),
        required=False,
    )
    number_of_days = forms.IntegerField(
        label=_("Lease Length (days)"),
        required=False,
        help_text=_(
            'Set to zero to schedule leases that start '
            'and end on the same day'),
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
            attrs={'placeholder': 'Tomorrow', 'class': 'datepicker'}),
    )
    end_time = forms.DateTimeField(
        label=_('End Time'),
        help_text=_(
            'Enter time with the format HH:MM (24-hour clock) or '
            'leave blank for same time as now'),
        error_messages={
            'invalid': _('Value should be time, '
                         'formatted HH:MM (24-hour clock)'),
        },
        input_formats=['%H:%M'],
        widget=forms.DateTimeInput(attrs={'placeholder': 'Same time as now'}),
        required=False,
    )

    class Meta(object):
        name = _("General")
        help_text_template = ("project/leases/"
                              "_lease_create_general_help.html")

    def __init__(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        super().__init__(request, context, *args, **kwargs)

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        try:
            tz = pytz.timezone(
                self.request.session.get('django_timezone',
                                         self.request.COOKIES.get(
                                             'django_timezone', 'UTC')
                                         )
            )
            extra['timezone'] = tz
            extra['offset'] = int(
                (datetime.datetime.now(tz).utcoffset().total_seconds() / 60) * -1)
        except Exception:
            exceptions.handle(self.request,
                              _("Can't get timezone."))

        return super().get_help_text(extra)

    def clean(self):

        cleaned_data = super(SetGeneralAction, self).clean()
        localtz = pytz.timezone(self.request.session.get(
            'django_timezone',
            self.request.COOKIES.get('django_timezone', 'UTC')))

        # straight copy
        # convert dates and times to datetime UTC
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")

        if start_date == '' or start_date is None:
            start_date = datetime.datetime.now(
                localtz) + datetime.timedelta(minutes=1)

        if start_time == '' or start_time is None:
            start_time = datetime.datetime.now(
                localtz) + datetime.timedelta(minutes=1)

        start_datetime = self.prepare_datetimes(start_date, start_time)

        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")

        if end_date == '' or end_date is None:
            end_date = datetime.datetime.now(
                localtz) + datetime.timedelta(days=1)

        if end_time == '' or end_time is None:
            end_time = datetime.datetime.now(
                localtz) + datetime.timedelta(days=1)

        end_datetime = self.prepare_datetimes(end_date, end_time)
        # plugging results
        cleaned_data['start_date'] = start_datetime
        cleaned_data['end_date'] = end_datetime
        # end copy

        if cleaned_data['start_date'] < datetime.datetime.now(tz=pytz.utc):
            raise forms.ValidationError("Start date must be in the future")

        if cleaned_data['start_date'] >= cleaned_data['end_date']:
            raise forms.ValidationError("Start date must be before end")

        # precheck for name conflicts
        leases = api.client.lease_list(self.request)
        if cleaned_data['name'] in {lease['name'] for lease in leases}:
            raise forms.ValidationError(
                "A lease with this name already exists.")

        return cleaned_data

    def prepare_datetimes(self, date_val, time_val):
        """
        Ensure the date and time are in user's timezone, then convert to UTC.
        """
        localtz = pytz.timezone(self.request.session.get(
            'django_timezone',
            self.request.COOKIES.get('django_timezone', 'UTC')))
        datetime_val = date_val.replace(
            hour=time_val.time().hour, minute=time_val.time().minute,
            tzinfo=None)
        datetime_val = localtz.localize(datetime_val)
        return datetime_val.astimezone(pytz.utc)


class SetGeneral(workflows.Step):
    action_class = SetGeneralAction
    template_name = 'project/leases/_create_lease_general_step.html'
    contributes = ("name", "start_date", "start_time",
                   "number_of_days", "end_date", "end_time")


class SetHostsAction(workflows.Action):
    min_hosts = forms.IntegerField(
        label=_('Minimum Number of Hosts'),
        required=False,
        help_text=_('Enter the minimum number of hosts to reserve.'),
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Minimum Number of Hosts')})
    )
    max_hosts = forms.IntegerField(
        label=_('Maximum Number of Hosts'),
        required=False,
        help_text=_('Enter the maximum number of hosts to reserve.'),
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Maximum Number of Hosts')})
    )
    computehost_resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(resource_type='computehost')
    )

    class Meta(object):
        name = _("Hosts")
        help_text_template = ("project/leases/"
                              "_lease_create_computehost_help.html")


class SetHosts(workflows.Step):
    action_class = SetHostsAction
    contributes = ("min_hosts", "max_hosts", "computehost_resource_properties")

    def allowed(self, request):
        return conf.host_reservation.get("enabled", False)


class SetNetworksAction(workflows.Action):
    if conf.network_reservation.get('enabled'):
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
            help_text=_(
                'Description to use when creating the Neutron network.'),
            widget=forms.TextInput(attrs={
                'class': 'switched',
                'data-switch-on': 'source',
                'data-source-network': _('Network Description')})
        )
        network_resource_properties = forms.CharField(
            label=_("Resource Properties"),
            required=False,
            help_text=_('Choose properties of the resource(s) to reserve.'),
            max_length=1024,
            widget=widgets.CapabilityWidget(resource_type='network')
        )
    if conf.floatingip_reservation.get('enabled'):
        network_ip_count = forms.IntegerField(
            label=_('Number of Floating IP Addresses Needed'),
            required=False,
            help_text=_(
                'If needed, enter the number of Floating IP addresses '
                'you would like to reserve.'),
            min_value=0,
            initial=0,
            widget=forms.NumberInput()
        )

    class Meta(object):
        name = _("Networks")
        help_text_template = ("project/leases/"
                              "_lease_create_network_help.html")

    def __init__(self, request, context, *args, **kwargs):
        self.request = request
        self.context = context
        super().__init__(request, context, *args, **kwargs)

    def get_help_text(self, extra_context=None):
        extra = {} if extra_context is None else dict(extra_context)
        extra['floating_ip_enabled'] = \
            conf.floatingip_reservation.get('enabled', False)
        extra['network_enabled'] = \
            conf.network_reservation.get('enabled', False)

        return super().get_help_text(extra)


class SetNetworks(workflows.Step):
    action_class = SetNetworksAction
    contributes = ("network_name", "network_description",
                   "network_ip_count", "network_resource_properties")

    def allowed(self, request):
        return conf.network_reservation.get("enabled", False) or \
            conf.floatingip_reservation.get("enabled", False)


class SetDevicesAction(workflows.Action):
    min_devices = forms.IntegerField(
        label=_('Minimum Number of Devices'),
        required=False,
        help_text=_('Enter the minimum number of devices to reserve.'),
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Minimum Number of Devices')})
    )
    max_devices = forms.IntegerField(
        label=_('Maximum Number of Devices'),
        required=False,
        help_text=_('Enter the maximum number of devices to reserve.'),
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'switched',
            'data-switch-on': 'source',
            'data-source-host': _('Maximum Number of Devices')})
    )
    device_resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(resource_type='device')
    )

    class Meta(object):
        name = _("Devices")


class SetDevices(workflows.Step):
    action_class = SetDevicesAction
    contributes = ("min_devices", "max_devices", "resource_properties")

    def allowed(self, request):
        return conf.device_reservation.get("enabled", False)


class CreateLease(workflows.Workflow):
    slug = "create_lease"
    name = _("Create Lease")
    finalize_button_name = _("Create")
    success_message = _('Request for creating a lease named "%s" '
                        'has been submitted.')
    failure_message = _('Unable to create the lease named "%s".')
    success_url = reverse_lazy('horizon:project:leases:index')
    multipart = True
    default_steps = [SetGeneral, SetHosts,
                     SetNetworks, SetDevices]

    def format_status_message(self, message):
        return message % self.context.get('name')

    def handle(self, request, data):
        reservations = []
        if (conf.host_reservation.get('enabled') and
                data['min_hosts'] > 0 and data['max_hosts'] > 0):
            res_props = data.get('computehost_resource_properties', '')
            reservations.append(
                {
                    'resource_type': 'physical:host',
                    'min': data['min_hosts'],
                    'max': data['max_hosts'],
                    'hypervisor_properties': '',
                    'resource_properties': res_props,
                })
        if (conf.floatingip_reservation.get('enabled') and
                data['network_ip_count'] > 0):
            network_id = api.client.get_floatingip_network_id(
                request, conf.floatingip_reservation.get('network_name_regex'))
            reservations.append(
                {
                    'resource_type': 'virtual:floatingip',
                    'network_id': network_id,
                    'amount': data['network_ip_count'],
                }
            )
        if conf.network_reservation.get('enabled') and data['network_name']:
            res_props = data.get('network_resource_properties', '')
            reservations.append(
                {
                    'resource_type': 'network',
                    'network_name': data['network_name'],
                    'network_description': data['network_description'],
                    'network_properties': '',
                    'resource_properties': res_props,
                })
        if (conf.device_reservation.get('enabled') and
                data['min_devices'] > 0 and data['max_devices'] > 0):
            res_props = data.get('device_resource_properties', '')
            reservations.append(
                {
                    'resource_type': 'device',
                    'min': data['min_devices'],
                    'max': data['max_devices'],
                    'resource_properties': res_props,
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
        cleaned_data = super(CreateLease, self).clean()
        if conf.host_reservation.get('enabled'):
            num_hosts = api.client.compute_host_available(
                self.request,
                cleaned_data['start_date'],
                cleaned_data['end_date'])
            if (cleaned_data['min_hosts'] > num_hosts):
                raise forms.ValidationError(_(
                    "Not enough hosts are available for this reservation "
                    "(minimum %s requested; %s available). Try adjusting "
                    "the number of hosts requested or the date range "
                    "for the reservation.")
                    % (cleaned_data['min_hosts'], num_hosts))
        if conf.device_reservation.get('enabled'):
            num_devices = api.client.device_available(
                self.request,
                cleaned_data['start_date'],
                cleaned_data['end_date'])
            if (cleaned_data['min_devices'] > num_devices):
                raise forms.ValidationError(_(
                    "Not enough devices are available for this reservation "
                    "(minimum %s requested; %s available). Try adjusting "
                    "the number of devices requested or the date range "
                    "for the reservation.")
                    % (cleaned_data['min_devices'], num_hosts))

        reserved_resource = False
        if (conf.host_reservation.get('enabled') and
                cleaned_data['min_hosts'] > 0):
            reserved_resource = True
        if (conf.network_reservation.get('enabled') and
                cleaned_data['network_name']):
            reserved_resource = True
        if (conf.floatingip_reservation.get('enabled') and
                cleaned_data['network_ip_count'] > 0):
            reserved_resource = True
        if (conf.device_reservation.get('enabled') and
                cleaned_data['min_device'] > 0):
            reserved_resource = True

        if not reserved_resource:
            raise forms.ValidationError("No resource to reserve.")
