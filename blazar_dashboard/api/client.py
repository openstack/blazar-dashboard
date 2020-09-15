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

import json
import logging

from horizon import exceptions
from horizon.utils.memoized import memoized
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
