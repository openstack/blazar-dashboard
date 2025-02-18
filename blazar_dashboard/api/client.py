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

from datetime import datetime
from datetime import timezone
from itertools import chain
import json
import logging

from blazar_dashboard import conf
from django.conf import settings
from horizon import exceptions
from horizon.utils.memoized import memoized
from keystoneauth1.identity import v3
from keystoneauth1 import session
from openstack_dashboard.api import base

from blazarclient import client as blazar_client


LOG = logging.getLogger(__name__)


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
        return json.loads(cpu_info_dict)

    def extra_capabilities(self):
        excaps = {}
        for k, v in self._apidict.items():
            if k not in self._attrs:
                excaps[k] = v
        return excaps


class Allocation(base.APIDictWrapper):

    _attrs = ['resource_id', 'reservations']


@memoized
def blazarclient(request):
    try:
        _ = base.url_for(request, 'reservation')
    except exceptions.ServiceCatalogException:
        LOG.debug('No Reservation service is configured.')
        return None

    auth_url = settings.OPENSTACK_KEYSTONE_URL
    project_id = request.user.project_id
    domain_id = request.session.get('domain_context')
    auth = v3.Token(auth_url,
                    request.user.token.id,
                    project_id=project_id,
                    project_domain_id=domain_id)
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    # If 'insecure' is True, 'verify' is False in all cases; otherwise
    # pass the cacert path if it is present, or True if no cacert.
    verify = not insecure and (cacert or True)
    sess = session.Session(auth=auth, verify=verify)

    return blazar_client.Client(session=sess)


def lease_list(request):
    """List the leases."""
    leases = blazarclient(request).lease.list()
    return [Lease(lease) for lease in leases]


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


def host_allocations_list(request):
    """List allocations for all hosts."""
    request_manager = blazarclient(request).host.request_manager
    resp, body = request_manager.get('/os-hosts/allocations')
    allocations = body['allocations']
    return [Allocation(a) for a in allocations]


def reservation_calendar(request):
    """Return a list of all scheduled leases."""

    def compute_host2dict(h):
        dictionary = dict(
            hypervisor_hostname=h.hypervisor_hostname, vcpus=h.vcpus,
            memory_mb=h.memory_mb, local_gb=h.local_gb, cpu_info=h.cpu_info,
            hypervisor_type=h.hypervisor_type,)
        # Ensure config attribute is copied over
        calendar_attribute = conf.host_reservation.get('calendar_attribute')
        dictionary[calendar_attribute] = (
            h[calendar_attribute]
        )
        return dictionary

    # NOTE: This filters by reservable hosts
    hosts_by_id = {h.id: h for h in host_list(request) if h.reservable}

    def host_reservation_dict(reservation, resource_id):
        host_reservation = dict(
            start_date=_parse_api_datestr(reservation['start_date']),
            end_date=_parse_api_datestr(reservation['end_date']),
            reservation_id=reservation['id'],
        )
        calendar_attribute = conf.host_reservation.get('calendar_attribute')
        host_reservation[calendar_attribute] = (
            hosts_by_id[resource_id][calendar_attribute]
        )

        return {k: v for k, v in host_reservation.items() if v is not None}

    host_reservations = [
        [host_reservation_dict(r, alloc.resource_id)
            for r in alloc.reservations
            if alloc.resource_id in hosts_by_id]
        for alloc in host_allocations_list(request)]

    compute_hosts = [compute_host2dict(h) for h in hosts_by_id.values()]

    return compute_hosts, list(chain(*host_reservations))


def _parse_api_datestr(datestr):
    if datestr is None:
        return datestr

    dateobj = datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%f")

    return dateobj.replace(tzinfo=timezone.utc)
