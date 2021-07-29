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
        required=True,
        error_messages={
            'required': _("Lease name is required!")},
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
        help_text_template = ("project/leases/create_lease/"
                              "_general_help.html")

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

        if not cleaned_data.get('name'):
            raise forms.ValidationError(
                "Lease name is required!")

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
    template_name = 'project/leases/create_lease/_general_step.html'
    contributes = ("name", "start_date", "start_time",
                   "number_of_days", "end_date", "end_time")


class SetHostsAction(workflows.Action):
    with_computehost = forms.BooleanField(label=_("Reserve Hosts"),
                                          initial=False,
                                          required=False,
                                          )
    min_hosts = forms.IntegerField(
        label=_('Minimum Number of Hosts'),
        required=False,
        help_text=_('Enter the minimum number of hosts to reserve.'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'create-lease-switch-on-computehost'
        })
    )
    max_hosts = forms.IntegerField(
        label=_('Maximum Number of Hosts'),
        required=False,
        help_text=_('Enter the maximum number of hosts to reserve.'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'create-lease-switch-on-computehost'
        })
    )
    computehost_resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(
            switchable_class='create-lease-switch-on-computehost',
            resource_type='computehost')
    )

    class Meta(object):
        name = _("Hosts")
        help_text_template = ("project/leases/create_lease/"
                              "_host_help.html")

    def clean(self):
        cleaned_data = super(SetHostsAction, self).clean()

        if not (cleaned_data.get('with_computehost') and
                cleaned_data.get('min_hosts')):
            return cleaned_data

        if (cleaned_data['min_hosts'] == 0 or cleaned_data['max_hosts'] == 0):
            raise forms.ValidationError(
                "No host is reserved! "
                "Clear \"Reserve Hosts\" checkbox "
                "if you don't need host resources.")

        if (cleaned_data['min_hosts'] > cleaned_data['max_hosts']):
            raise forms.ValidationError(
                "Max hosts is less than min hosts!")

        return cleaned_data


class SetHosts(workflows.Step):
    action_class = SetHostsAction
    template_name = 'project/leases/create_lease/_host_step.html'
    contributes = ("with_computehost", "min_hosts", "max_hosts",
                   "computehost_resource_properties")

    def allowed(self, request):
        return conf.host_reservation.get("enabled", False)


class SetNetworksAction(workflows.Action):
    if conf.network_reservation.get('enabled', False):
        with_network = forms.BooleanField(label=_("Reserve Network"),
                                          initial=False,
                                          required=False,
                                          )
        network_name = forms.CharField(
            label=_('Network Name'),
            required=False,
            help_text=_('Name to use when creating the Neutron network.'),
            error_messages={
                'required': _('Please specify "Network Name"')},
            widget=forms.TextInput(attrs={
                'class': 'create-lease-switch-on-network'
            })
        )
        network_description = forms.CharField(
            label=_('Network Description'),
            required=False,
            help_text=_(
                'Description to use when creating the Neutron network.'),
            widget=forms.TextInput(attrs={
                'class': 'create-lease-switch-on-network'
            })
        )
        network_resource_properties = forms.CharField(
            label=_("Resource Properties"),
            required=False,
            help_text=_('Choose properties of the resource(s) to reserve.'),
            max_length=1024,
            widget=widgets.CapabilityWidget(
                switchable_class='create-lease-switch-on-network',
                resource_type='network')
        )
    if conf.floatingip_reservation.get('enabled', False):
        with_floatingip = forms.BooleanField(label=_("Reserve Floating IPs"),
                                             initial=False,
                                             required=False,
                                             )
        network_ip_count = forms.IntegerField(
            label=_('Number of Floating IP Addresses Needed'),
            required=False,
            help_text=_(
                'If needed, enter the number of Floating IP addresses '
                'you would like to reserve.'),
            min_value=0,
            initial=0,
            widget=forms.NumberInput(attrs={
                'class': 'create-lease-switch-on-floatingip'
            })
        )

    class Meta(object):
        name = _("Networks")
        help_text_template = ("project/leases/create_lease/"
                              "_network_help.html")

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

    def clean(self):
        cleaned_data = super(SetNetworksAction, self).clean()

        if not cleaned_data.get('with_network'):
            return cleaned_data

        if (not cleaned_data.get('network_name') and
                cleaned_data.get('network_ip_count', 0) == 0):
            raise forms.ValidationError(
                "No network resource is reserved! "
                "Clear \"Reserve Networks\" checkbox "
                "if you don't need network resources.")

        return cleaned_data


class SetNetworks(workflows.Step):
    action_class = SetNetworksAction
    template_name = 'project/leases/create_lease/_network_step.html'
    contributes = ("with_network", "network_name", "network_description",
                   "with_floatingip", "network_ip_count", "network_resource_properties")

    def allowed(self, request):
        return (conf.network_reservation.get("enabled", False) or
                conf.floatingip_reservation.get("enabled", False))


class SetDevicesAction(workflows.Action):
    with_device = forms.BooleanField(label=_("Reserve Devices"),
                                     initial=False,
                                     required=False,
                                     )
    min_devices = forms.IntegerField(
        label=_('Minimum Number of Devices'),
        required=False,
        help_text=_('Enter the minimum number of devices to reserve.'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'create-lease-switch-on-device'
        })
    )
    max_devices = forms.IntegerField(
        label=_('Maximum Number of Devices'),
        required=False,
        help_text=_('Enter the maximum number of devices to reserve.'),
        min_value=0,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'create-lease-switch-on-device'
        })
    )
    device_resource_properties = forms.CharField(
        label=_("Resource Properties"),
        required=False,
        help_text=_('Choose properties of the resource(s) to reserve.'),
        max_length=1024,
        widget=widgets.CapabilityWidget(
            switchable_class='create-lease-switch-on-device',
            resource_type='device')
    )

    class Meta(object):
        name = _("Devices")

    def clean(self):
        cleaned_data = super(SetDevicesAction, self).clean()

        if (not cleaned_data.get('with_device') or
                not cleaned_data.get('min_devices')):
            return cleaned_data

        if (cleaned_data['min_devices'] == 0 or
                cleaned_data['max_devices'] == 0):
            raise forms.ValidationError(
                "No device is reserved! "
                "Clear \"Reserve Devices\" checkbox "
                "if you don't need device resources.")

        if (cleaned_data['min_devices'] > cleaned_data['max_devices']):
            raise forms.ValidationError(
                "Max devices is less than min devices!")

        return cleaned_data


class SetDevices(workflows.Step):
    action_class = SetDevicesAction
    template_name = 'project/leases/create_lease/_device_step.html'
    contributes = ("with_device", "min_devices",
                   "max_devices", "device_resource_properties")

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
    wizard = True
    default_steps = [SetGeneral, SetHosts,
                     SetNetworks, SetDevices]

    def format_status_message(self, message):
        return message % self.context.get('name')

    def is_valid(self):
        try:
            # check for name conflicts
            leases = api.client.lease_list(self.request)
            if self.context.get('name') in {lease['name'] for lease in leases}:
                raise forms.ValidationError(
                    "A lease with this name already exists.")

            # check if any resource is reserved
            if (not self.context.get('with_computehost', False) and
                not self.context.get('with_network', False) and
                not self.context.get('with_floatingip', False) and
                    not self.context.get('with_device', False)):
                raise forms.ValidationError(
                    'Please specify at least one reservation')

            # check if there is enough hosts
            if self.context.get('with_computehost', False):
                num_hosts = api.client.compute_host_available(
                    self.request,
                    self.context.get('start_date'),
                    self.context.get('end_date'))
                if (self.context.get('min_hosts') > num_hosts):
                    raise forms.ValidationError(_(
                        "Not enough hosts are available for this reservation "
                        "(minimum %s requested; %s available). Try adjusting "
                        "the number of hosts requested or the date range "
                        "for the reservation.")
                        % (self.context.get('min_hosts'), num_hosts))

            # check if there is enough devices
            if self.context.get('with_device', False):
                num_devices = api.client.device_available(
                    self.request,
                    self.context.get('start_date'),
                    self.context.get('end_date'))
                if (self.context.get('min_devices') > num_devices):
                    raise forms.ValidationError(_(
                        "Not enough devices are available for this reservation "
                        "(minimum %s requested; %s available). Try adjusting "
                        "the number of hosts requested or the date range "
                        "for the reservation.")
                        % (self.context.get('min_devices'), num_devices))

        except Exception as e:
            exceptions.handle(self.request,
                              message=str(e).strip("['']"))
            return False

        return super(CreateLease, self).is_valid()

    def handle(self, request, data):
        reservations = []
        if (data.get('with_computehost', False) and
            conf.host_reservation.get('enabled', False) and
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
        if (data.get('with_floatingip', False) and
            conf.floatingip_reservation.get('enabled', False) and
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
        if (data.get('with_network', False) and
            conf.network_reservation.get('enabled', False) and
                data['network_name']):
            res_props = data.get('network_resource_properties', '')
            reservations.append(
                {
                    'resource_type': 'network',
                    'network_name': data['network_name'],
                    'network_description': data['network_description'],
                    'network_properties': '',
                    'resource_properties': res_props,
                })
        if (data.get('with_device', False) and
            conf.device_reservation.get('enabled', False) and
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


class UpdateGeneralAction(workflows.Action):

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

    class Meta(object):
        name = _('General')


class UpdateGeneral(workflows.Step):
    action_class = UpdateGeneralAction
    contributes = ("lease_name", "prolong_for", "reduce_by",
                   "reservations")


class UpdateHostsAction(workflows.Action):
    min_hosts = forms.IntegerField(
        label=_('Minimum Number of Hosts'),
        required=False,
        help_text=_('Enter the updated minimum number of hosts to reserve.'),
        min_value=1
    )
    max_hosts = forms.IntegerField(
        label=_('Maximum Number of Hosts'),
        required=False,
        help_text=_('Enter the updated maximum number of hosts to reserve.'),
        min_value=1
    )

    class Meta(object):
        name = _('Hosts')
        help_text = _("For advance reservations that haven’t yet started, "
                      "the node count can be increased or decreased. "
                      "For reservations already started, "
                      "only new nodes can be added.")

    def clean(self):
        cleaned_data = super(UpdateHostsAction, self).clean()
        min_hosts = cleaned_data.get("min_hosts")
        max_hosts = cleaned_data.get("max_hosts")

        if (min_hosts or max_hosts) and not (min_hosts and max_hosts):
            raise forms.ValidationError("You must provide both min_hosts and "
                                        "max_hosts.")

        return cleaned_data


class UpdateHosts(workflows.Step):
    action_class = UpdateHostsAction
    contributes = ("min_hosts", "max_hosts")

    def allowed(self, request):
        return conf.host_reservation.get("enabled", False)


class UpdateLease(workflows.Workflow):
    slug = "update_lease"
    name = _("Update Lease")
    finalize_button_name = _("Update")
    success_message = _('Request for updating a lease named "%s" '
                        'has been submitted.')
    failure_message = _('Unable to update the lease named "%s".')
    success_url = reverse_lazy('horizon:project:leases:index')
    wizard = True
    default_steps = [UpdateGeneral]

    def __init__(self, request=None, context_seed=None,
                 entry_point=None, *args, **kwargs):
        resource_types = []
        for reservation in context_seed['lease'].reservations:
            resource_types.append(reservation['resource_type'])

        self.lease_id = context_seed['lease'].id

        self.is_hostreservation_included = False
        if 'physical:host' in resource_types:
            self.is_hostreservation_included = True
            self.register(UpdateHosts)

        super(UpdateLease, self).__init__(
            request, context_seed, entry_point, *args, **kwargs)

    def format_status_message(self, message):
        return message % self.context.get('lease_name')

    def handle(self, request, data):
        lease_id = self.lease_id
        is_update = False

        fields = {}

        lease_name = data.get('lease_name', None)
        if lease_name:
            fields['name'] = lease_name
            is_update = True

        try:
            prolong = float((data.get('prolong_for') or '0s').rstrip('s'))
            reduce = float((data.get('reduce_by') or '0s').rstrip('s'))
        except ValueError as e:
            LOG.error('Error updating lease: %s', e)
            exceptions.handle(request, message="Invalid value provided.")
            return

        net_mins = round((prolong - reduce) / 60.0)
        min_string = '{:.0f}m'.format(abs(net_mins))
        if net_mins > 0:
            fields['prolong_for'] = min_string
            is_update = True
        elif net_mins < 0:
            fields['reduce_by'] = min_string
            is_update = True

        if conf.host_reservation.get("enabled", False) and \
                self.is_hostreservation_included:
            min_hosts = data.get('min_hosts')
            max_hosts = data.get('max_hosts')
            if min_hosts and max_hosts:
                if (min_hosts or max_hosts) and not (min_hosts and max_hosts):
                    raise forms.ValidationError("You must provide both "
                                                "min_hosts and max_hosts.")
                try:
                    min_hosts = int(data.get('min_hosts'))
                    max_hosts = int(data.get('max_hosts'))
                except ValueError as e:
                    LOG.error('Error updating lease: %s', e)
                    exceptions.handle(
                        request, message="Invalid value provided.")
                    return

                lease = api.client.lease_get(self.request, lease_id)
                fields['reservations'] = lease['reservations']
                if len(fields['reservations']) != 1:
                    messages.error(request, "Cannot update node count for a lease "
                                            "with multiple reservations.")
                    return
                fields['reservations'][0]['min'] = min_hosts
                fields['reservations'][0]['max'] = min_hosts
                is_update = True

        reservations = data.get('reservations', None)
        if reservations:
            fields['reservations'] = reservations
            is_update = True

        if not is_update:
            raise forms.ValidationError("Nothing to update.")

        try:
            api.client.lease_update(self.request, lease_id=lease_id, **fields)
            messages.success(request, _("Lease update started."))
            return True
        except Exception as e:
            LOG.error('Error updating lease: %s', e)
            exceptions.handle(request,
                              message="An error occurred while updating this "
                                      "lease: %s. Please try again." % e)
