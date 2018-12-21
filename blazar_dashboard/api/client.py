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

from collections import OrderedDict
import logging
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
              'service_name', 'trust_id', 'reservable']

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
    start_date_str = start_date.strftime('%Y-%m-%d %H:%M')
    end_date_str = end_date.strftime('%Y-%m-%d %H:%M')
    cursor = get_cursor_for_request(request)
    cursor.execute("""
        select count(*) as available
        from computehosts ch
        where ch.id not in (
            select ch.id
            from computehosts ch
            join computehost_allocations cha on cha.`compute_host_id` = ch.`id`
            join reservations r on r.id = cha.`reservation_id`
            join leases l on l.`id` = r.`lease_id`
            where
                r.deleted IS NULL and
                ((l.`start_date` > %s and l.`start_date` < %s)
                or (l.`end_date` > %s and l.`end_date` < %s)
                or (l.`start_date` < %s and l.`end_date` > %s))
        )
        """, [start_date_str, end_date_str, start_date_str, end_date_str, start_date_str, end_date_str])
    count = cursor.fetchone()[0]
    return count


def node_in_lease(request, lease_id, active_only=True):
    sql = '''\
    SELECT
        c.hypervisor_hostname,
        ca.deleted
    FROM
        computehost_allocations AS ca
        JOIN computehosts AS c ON c.id = ca.compute_host_id
        JOIN reservations AS r ON r.id = ca.reservation_id
        JOIN leases AS l ON l.id = r.lease_id
    WHERE
        l.id = %s
    '''
    if active_only:
        sql += " AND ca.deleted IS NULL"
    sql_args = (lease_id,)

    cursor = get_cursor_for_request(request)
    cursor.execute(sql, sql_args)
    hypervisor_hostnames = dictfetchall(cursor)
    return hypervisor_hostnames


def compute_host_list(request, node_types=False):
    """Return a list of compute hosts available for reservation"""
    sql = '''\
    SELECT
        hypervisor_hostname,
        vcpus,
        memory_mb,
        local_gb,
        cpu_info,
        hypervisor_type
    FROM
        computehosts
    '''
    cursor = get_cursor_for_request(request)
    cursor.execute(sql)
    compute_hosts = dictfetchall(cursor)

    if node_types:
        node_types = node_type_map(cursor=cursor)
        for ch in compute_hosts:
            ch['node_type'] = node_types.get(ch['hypervisor_hostname'], 'unknown')

    return compute_hosts


def node_type_map(request=None, cursor=None):
    if cursor is None:
        cursor = get_cursor_for_request(request)
    sql = '''\
    SELECT ch.hypervisor_hostname AS id, nt.node_type
    FROM blazar.computehosts AS ch
    INNER JOIN (
        SELECT ex.computehost_id AS id, ex.capability_value AS node_type
        FROM blazar.computehost_extra_capabilities AS ex
        INNER JOIN (
            SELECT id, MAX(created_at)
            FROM blazar.computehost_extra_capabilities
            WHERE capability_name = 'node_type'
            GROUP BY computehost_id
        ) AS exl
        ON ex.id = exl.id
    ) AS nt
    ON ch.id = nt.id;
    '''
    cursor.execute(sql)
    node_types = dict(cursor.fetchall())
    return node_types


def reservation_calendar(request):
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
        c.hypervisor_hostname
    FROM
        computehost_allocations cha
        JOIN computehosts c ON c.id = cha.compute_host_id
        JOIN reservations r ON r.id = cha.reservation_id
        JOIN leases l ON l.id = r.lease_id
    WHERE
        r.deleted IS NULL
        AND cha.deleted IS NULL
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
