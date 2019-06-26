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

from collections import OrderedDict, defaultdict
from datetime import datetime
from itertools import chain
import logging
from pytz import UTC
from six.moves.urllib.parse import urlparse

from django.db import connections
from django.utils.translation import ugettext_lazy as _
import six

from horizon import exceptions
from horizon.utils.memoized import memoized
from openstack_dashboard.api import base

from blazarclient import client as blazar_client


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
              'service_name', 'trust_id', 'reservable', 'node_type']

    def __init__(self, apiresource):
        super(Host, self).__init__(apiresource)

    def cpu_info_dict(self):
        cpu_info_dict = getattr(self, 'cpu_info', '{}')
        if not cpu_info_dict:
            cpu_info_dict = '{}'
        return eval(cpu_info_dict)

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


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def get_cursor_for_request(request):
    """
    Get a cursor for the database in the request's region

    The DATABASES setting must be configured with all the regions to be used
    named like "blazar-CHI@TACC", "blazar-CHI@UC", and so on.
    """
    region = request.session.get('services_region')
    connection = connections['blazar-' + region]
    return connection.cursor()


def compute_host_available(request, start_date, end_date):
    """
    Return the number of compute hosts available for reservation for the entire
    specified date range.
    """
    def check_host_unavailable(reservation):
        lease_start = datetime.strptime(
            reservation['start_date'],
            '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=UTC)
        lease_end = datetime.strptime(
            reservation['end_date'],
            '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=UTC)

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


def node_in_lease(request, lease_id):
    """Return list of hypervisor_hostnames in a lease."""
    hypervisor_by_host_id = {
        h.id: h.hypervisor_hostname for h in host_list(request)}

    return [
        dict(
            hypervisor_hostname=hypervisor_by_host_id[h.resource_id],
            deleted=False)
        for h in host_allocations_list(request)
        if any((r['lease_id'] == lease_id) for r in h.reservations)]


def compute_host_list(request):
    """Return a list of compute hosts available for reservation."""
    def compute_host2dict(h):
        host_dict = dict(
            hypervisor_hostname=h.hypervisor_hostname, vcpus=h.vcpus,
            memory_mb=h.memory_mb, local_gb=h.local_gb, cpu_info=h.cpu_info,
            hypervisor_type=h.hypervisor_type, node_type=h.node_type)

        return host_dict

    return [compute_host2dict(h) for h in host_list(request)]


def reservation_calendar(request):
    """Return a list of all scheduled leases."""

    hypervisor_by_host_id = {
        h.id: h.hypervisor_hostname for h in host_list(request)}

    def host_reservation_dict(reservation, resource_id):
        host_reservation = dict(
            name=reservation.get('name', None),
            project_id=reservation.get('project_id', None),
            start_date=reservation.get('start_date', None),
            end_date=reservation.get('end_date', None),
            id=reservation.get('id', None),
            status=reservation.get('status', None),
            hypervisor_hostname=hypervisor_by_host_id[resource_id])

        return {k: v for k, v in host_reservation.items() if v is not None}

    host_reservations = [
        [host_reservation_dict(r, alloc.resource_id)
            for r in alloc.reservations]
        for alloc in host_allocations_list(request)]

    return list(chain(*host_reservations))


def network_list(request):
    """Return a list of networks available for reservation"""
    # TODO > USE CLIENT
    sql = '''\
    SELECT
        physical_network,
        segment_id
    FROM
        network_segments
    '''
    cursor = get_cursor_for_request(request)
    cursor.execute(sql)
    networks = dictfetchall(cursor)

    return networks


def network_reservation_calendar(request):
    """Return a list of all scheduled leases."""
    cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT
        l.name,
        l.project_id,
        l.start_date,
        l.end_date,
        r.id,
        r.status,
        n.segment_id
    FROM
        network_allocations na
        JOIN network_segments n ON n.id = na.network_id
        JOIN reservations r ON r.id = na.reservation_id
        JOIN leases l ON l.id = r.lease_id
    WHERE
        r.deleted IS NULL
        AND na.deleted IS NULL
    ORDER BY
        start_date,
        project_id;
    '''
    cursor.execute(sql)
    host_reservations = dictfetchall(cursor)

    return host_reservations


def extra_capability_names(request):
    """
    Return all the names for possible selections.
    """
    cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT DISTINCT
        capability_name
    FROM
        computehost_extra_capabilities
    '''
    cursor.execute(sql)
    # available = dictfetchall(cursor)
    available = [row[0] for row in cursor.fetchall()]

    cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT DISTINCT
        capability_name
    FROM
        networksegment_extra_capabilities
    '''
    cursor.execute(sql)
    # available = dictfetchall(cursor)
    available += [row[0] for row in cursor.fetchall()]
    return list(set(available))


def extra_capability_values(request, name):
    """
    Return the capabilities with a given "name". The client can cache/combine
    the rows together to build up a full copy of the extra capabilities table
    if they really want. Then they can do the "what-if" filtering themselves
    to count hosts.

    They could maybe mix that with the calendar data to even see if the chosen
    number of hosts are free. Might need to do the lookup between
    computehost_id (small integers) and the UUID via the uid name:value pairs.
    """
    cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT
        id, computehost_id, capability_name, capability_value
    FROM
        computehost_extra_capabilities
    WHERE
        capability_name = %s
    '''
    cursor.execute(sql, [name])
    rows = dictfetchall(cursor)

    cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT
        id, network_id, capability_name, capability_value
    FROM
        networksegment_extra_capabilities
    WHERE
        capability_name = %s
    '''
    cursor.execute(sql, [name])
    rows += dictfetchall(cursor)

    return rows
