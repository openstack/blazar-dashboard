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

from __future__ import absolute_import

from datetime import datetime
from itertools import chain
import re

from pytz import UTC

from blazarclient import client as blazar_client
from collections import OrderedDict
from django.db import connections
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon.utils.memoized import memoized
import json
import logging
from openstack_dashboard.api import base
from openstack_dashboard.api import neutron


LOG = logging.getLogger(__name__)
LEASE_DATE_FORMAT = "%Y-%m-%d %H:%M"

PRETTY_TYPE_NAMES = OrderedDict([
    ('compute', _('Compute Node (default)')),
    ('storage', _('Storage')),
    ('gpu_k80', _('GPU (K80)')),
    ('gpu_m40', _('GPU (M40)')),
    ('gpu_p100', _('GPU (P100)')),
    ('compute_ib', _('Infiniband Support')),
    ('storage_hierarchy', _('Storage Hierarchy')),
    ('fpga', _('FPGA')),
    ('lowpower_xeon', _('Low power Xeon')),
    ('atom', _('Atom')),
    ('arm64', _('ARM64')),
])

PRETTY_EXTRA_LABELS = {
    "name": _("Reserved by")
}

class Lease(base.APIDictWrapper):
    """Represents one Blazar lease."""

    _attrs = ['id', 'name', 'start_date', 'end_date', 'user_id', 'project_id',
              'before_end_date', 'status', 'degraded']

    def __init__(self, apiresource):
        super(Lease, self).__init__(apiresource)


class Host(base.APIDictWrapper):
    """Represents one Blazar host."""

    _attrs = ['id', 'hypervisor_hostname', 'hypervisor_type',
              'hypervisor_version', 'vcpus', 'cpu_info', 'memory_mb',
              'local_gb', 'status', 'created_at', 'updated_at',
              'service_name', 'trust_id', 'reservable', 'node_type',
              'node_name']

    def __init__(self, apiresource):
        super(Host, self).__init__(apiresource)

    def cpu_info_dict(self):
        cpu_info_dict = getattr(self, 'cpu_info', '{}')
        if not cpu_info_dict:
            cpu_info_dict = '{}'
        return json.loads(cpu_info_dict)

    def extra_capabilities(self):
        excaps = {}
        for k, v in self._apidict.items():
            if k not in self._attrs:
                excaps[k] = v
        return excaps


class Network(base.APIDictWrapper):
    """Represents one Blazar network."""

    _attrs = ['id', 'network_type', 'physical_network', 'segment_id',
              'created_at', 'updated_at']

    def __init__(self, apiresource):
        super(Network, self).__init__(apiresource)

    def extra_capabilities(self):
        excaps = {}
        for k, v in self._apidict.items():
            if k not in self._attrs:
                excaps[k] = v
        return excaps


class Device(base.APIDictWrapper):
    """Represents one Blazar device."""

    _attrs = ['id', 'name', 'device_type', 'device_driver']

    def __init__(self, apiresource):
        super(Device, self).__init__(apiresource)

    def extra_capabilities(self):
        excaps = {}
        for k, v in self._apidict.items():
            if k not in self._attrs:
                excaps[k] = v
        return excaps


class Allocation(base.APIDictWrapper):

    _attrs = ['resource_id', 'reservations']

    def __init__(self, apiresource):
        super(Allocation, self).__init__(apiresource)


class ExtraCapability(base.APIDictWrapper):

    _attrs = ['property', 'private', 'capability_values']

    def __init__(self, apiresource):
        super(ExtraCapability, self).__init__(apiresource)


@memoized
def blazarclient(request):
    try:
        api_url = base.url_for(request, 'reservation')
    except exceptions.ServiceCatalogException:
        LOG.debug('No Reservation service is configured.')
        return None

    LOG.debug('blazarclient connection created using the token "%s" and url'
              '"%s"' % (request.user.token.id, api_url))
    return blazar_client.Client(
        blazar_url=api_url,
        auth_token=request.user.token.id)


def lease_list(request):
    """List the leases."""
    leases = blazarclient(request).lease.list()
    return [Lease(l) for l in leases]


def lease_get(request, lease_id):
    """Get a lease."""
    lease = blazarclient(request).lease.get(lease_id)
    return Lease(lease)


def lease_create(request, name, start, end, reservations, events):
    """Create a lease."""
    lease = blazarclient(request).lease.create(
        name, start, end, reservations, events)
    return Lease(lease)


def lease_update(request, lease_id, **kwargs):
    """Update a lease."""
    lease = blazarclient(request).lease.update(lease_id, **kwargs)
    return Lease(lease)


def lease_delete(request, lease_id):
    """Delete a lease."""
    blazarclient(request).lease.delete(lease_id)


def host_list(request):
    """List hosts."""
    hosts = blazarclient(request).host.list()
    return [Host(h) for h in hosts]


def host_get(request, host_id):
    """Get a host."""
    host = blazarclient(request).host.get(host_id)
    return Host(host)


def host_create(request, name, **kwargs):
    """Create a host."""
    host = blazarclient(request).host.create(name, **kwargs)
    return Host(host)


def host_update(request, host_id, values):
    """Update a host."""
    host = blazarclient(request).host.update(host_id, values)
    return Host(host)


def host_delete(request, host_id):
    """Delete a host."""
    blazarclient(request).host.delete(host_id)


def host_get_allocation(request, host_id):
    """Get a host's allocations."""
    allocation = blazarclient(request).host.get_allocation(host_id)
    return Allocation(allocation)


def host_allocations_list(request):
    """List allocations for all hosts."""
    allocations = blazarclient(request).host.list_allocations()
    return [Allocation(a) for a in allocations]


def host_capabilities_list(request):
    extra_capabilities = blazarclient(
        request).host.list_capabilities(detail=True)
    return [ExtraCapability(e) for e in extra_capabilities]


def network_list(request):
    """List networks."""
    networks = blazarclient(request).network.list()
    return [Network(n) for n in networks]


def network_allocations_list(request):
    """List allocations for all networks."""
    allocations = blazarclient(request).network.list_allocations()
    return [Allocation(a) for a in allocations]


def network_capabilities_list(request):
    extra_capabilities = blazarclient(
        request).network.list_capabilities(detail=True)
    extra_capabilities.append({'property': 'physical_network',
                               'private': False,
                               'capability_values': ['physnet1', 'vlan']})
    return [ExtraCapability(e) for e in extra_capabilities]


def device_list(request):
    """List devices."""
    devices = blazarclient(request).device.list()
    return [Device(d) for d in devices]


def device_allocations_list(request):
    """List allocations for all devices."""
    allocations = blazarclient(request).device.list_allocations()
    return [Allocation(a) for a in allocations]


def device_capabilities_list(request):
    extra_capabilities = blazarclient(
        request).device.list_capabilities(detail=True)
    return [ExtraCapability(e) for e in extra_capabilities]


def compute_host_available(request, start_date, end_date):
    """
    Return the number of compute hosts available for reservation for the entire
    specified date range.
    """
    def check_host_unavailable(reservation):
        lease_start = _parse_api_datestr(reservation['start_date'])
        lease_end = _parse_api_datestr(reservation['end_date'])

        if (lease_start > start_date and lease_start < end_date):
            return True
        elif (lease_end > start_date and lease_end < end_date):
            return True
        elif (lease_start < start_date and lease_end > end_date):
            return True
        else:
            return False

    available_hosts = [
        h for h in host_allocations_list(request)
        if (not any([check_host_unavailable(r) for r in h.reservations]) or
            not h.reservations)]

    return len(available_hosts)


def device_available(request, start_date, end_date):
    """
    Return the number of devices available for reservation for the entire
    specified date range.
    """
    def check_device_unavailable(reservation):
        lease_start = _parse_api_datestr(reservation['start_date'])
        lease_end = _parse_api_datestr(reservation['end_date'])

        if (lease_start > start_date and lease_start < end_date):
            return True
        elif (lease_end > start_date and lease_end < end_date):
            return True
        elif (lease_start < start_date and lease_end > end_date):
            return True
        else:
            return False

    available_devices = [
        d for d in device_allocations_list(request)
        if (not any([check_device_unavailable(r) for r in d.reservations]) or
            not d.reservations)]

    return len(available_devices)


def compute_host_display_name(host):
    return getattr(host, 'node_name', 'node{}'.format(host.id))


def nodes_in_lease(request, lease):
    """Return list of hypervisor_hostnames in a lease."""
    if not any(
            r['resource_type'] == 'physical:host' for r in lease['reservations']):
        return []

    hypervisor_by_host_id = {
        h.id: {
            'hypervisor_hostname': h.hypervisor_hostname,
            'node_name': compute_host_display_name(h)}
        for h in host_list(request)}

    return [
        dict(
            hypervisor_hostname=hypervisor_by_host_id[h.resource_id].get(
                'hypervisor_hostname'),
            node_name=hypervisor_by_host_id[h.resource_id].get('node_name'),
            deleted=False)
        for h in host_allocations_list(request)
        if any((r['lease_id'] == lease['id']) for r in h.reservations)]


def reservation_calendar(request):
    """Return a list of all scheduled leases."""

    def compute_host2dict(h):
        return dict(
            hypervisor_hostname=h.hypervisor_hostname, vcpus=h.vcpus,
            memory_mb=h.memory_mb, local_gb=h.local_gb, cpu_info=h.cpu_info,
            hypervisor_type=h.hypervisor_type, node_type=h.node_type,
            node_name=compute_host_display_name(h))

    hosts_by_id = {h.id: h for h in host_list(request) if h.reservable}

    def host_reservation_dict(reservation, resource_id):
        host_reservation = dict(
            name=reservation.get('name'),
            project_id=reservation.get('project_id'),
            start_date=_parse_api_datestr(reservation['start_date']),
            end_date=_parse_api_datestr(reservation['end_date']),
            id=reservation['id'],
            status=reservation.get('status'),
            hypervisor_hostname=hosts_by_id[resource_id].hypervisor_hostname,
            node_name=compute_host_display_name(hosts_by_id[resource_id]))

        return {k: v for k, v in host_reservation.items() if v is not None}

    host_reservations = [
        [host_reservation_dict(r, alloc.resource_id)
            for r in alloc.reservations
            if alloc.resource_id in hosts_by_id]
        for alloc in host_allocations_list(request)]

    compute_hosts = [compute_host2dict(h) for h in hosts_by_id.values()]

    return compute_hosts, list(chain(*host_reservations))


def network_reservation_calendar(request):
    """Return a list of all scheduled network leases."""

    def network2dict(n):
        return dict(
            network_type=n.network_type, physical_network=n.physical_network,
            segment_id=n.segment_id)

    networks_by_id = {n.id: n for n in network_list(request)}

    def network_reservation_dict(reservation, resource_id):
        network_reservation = dict(
            name=reservation.get('name'),
            project_id=reservation.get('project_id'),
            start_date=_parse_api_datestr(reservation['start_date']),
            end_date=_parse_api_datestr(reservation['end_date']),
            id=reservation['id'],
            status=reservation.get('status'),
            segment_id=networks_by_id[resource_id].segment_id)

        return {k: v for k, v in network_reservation.items() if v is not None}

    network_reservations = [
        [network_reservation_dict(r, alloc.resource_id)
            for r in alloc.reservations
            if alloc.resource_id in networks_by_id]
        for alloc in network_allocations_list(request)]

    networks = [network2dict(n) for n in networks_by_id.values()]

    return networks, list(chain(*network_reservations))


def device_reservation_calendar(request):
    """Return a list of all scheduled device leases."""

    def device2dict(d):
        device_dict = dict(
            device_name=d.name, device_type=d.device_type,
            device_driver=d.device_driver, vendor=d.vendor)
        # Copy these keys if they exist
        for key in ["authorized_projects", "restricted_reason"]:
            if key in d:
                device_dict[key] = d[key]
        return device_dict

    devices_by_id = {d.id: d for d in device_list(request)}

    def device_reservation_dict(reservation, resource_id):
        device_reservation = dict(
            name=reservation.get('name'),
            project_id=reservation.get('project_id'),
            start_date=_parse_api_datestr(reservation['start_date']),
            end_date=_parse_api_datestr(reservation['end_date']),
            id=reservation['id'],
            status=reservation.get('status'),
            device_name=devices_by_id[resource_id].name,
            extras=[(PRETTY_EXTRA_LABELS[key], value) for key, value in reservation.get("extras").items()]
        )

        return {k: v for k, v in device_reservation.items() if v is not None}

    device_reservations = [
        [device_reservation_dict(r, alloc.resource_id)
            for r in alloc.reservations
            if alloc.resource_id in devices_by_id]
        for alloc in device_allocations_list(request)]

    devices = [device2dict(d) for d in devices_by_id.values()]

    return devices, list(chain(*device_reservations))


def computehost_extra_capabilities(request):
    return {
        x.property: x.capability_values for x
        in host_capabilities_list(request)}


def network_extra_capabilities(request):
    return {
        x.property: x.capability_values for x
        in network_capabilities_list(request)}


def device_extra_capabilities(request):
    return {
        x.property: x.capability_values for x
        in device_capabilities_list(request)}


def get_floatingip_network_id(request, network_name_regex):
    """Return default network id for floatingip reservation"""
    pattern = re.compile(network_name_regex)
    networks = [
        n['id'] for n in neutron.network_list(request)
        if re.match(pattern, str(n['name']))]

    return networks[0]


def _parse_api_datestr(datestr):
    if datestr is None:
        return datestr

    dateobj = datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%f")

    return dateobj.replace(tzinfo=UTC)
