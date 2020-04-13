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

from openstack_dashboard.test.test_data import utils

from blazar_dashboard import api


lease_sample1 = {
    'status': None,
    'user_id': None,
    'name': 'lease-1',
    'end_date': '2030-06-30T18:00:00.000000',
    'reservations': [
        {
            'status': 'pending',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'min': 1,
            'max': 1,
            'hypervisor_properties': '',
            'resource_id': '3850a831-8c08-49c4-b703-d804284a6baf',
            'resource_properties': '[">=", "$vcpus", "2"]',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'id': '087bc740-6d2d-410b-9d47-c7b2b55a9d36',
            'resource_type': 'physical:host',
            'missing_resources': False,
            'resources_changed': False
        }
    ],
    'created_at': '2017-06-27 15:00:00',
    'updated_at': None,
    'events': [
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'start_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2017-06-27T18:00:00.000000',
            'id': '188a8584-f832-4df9-9a4a-51e6364420ff'
        },
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'end_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2030-06-30T18:00:00.000000',
            'id': '277d6436-dfcb-4eae-ae5e-ac7fa9c2fd56'
        },
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'before_end_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2030-06-28T18:00:00.000000',
            'id': 'f583af71-ca21-4b66-87de-52211d118029'
        }
    ],
    'id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
    'project_id': 'aa45f56901ef45ee95e3d211097c0ea3',
    'start_date': '2017-06-27T18:00:00.000000',
    'trust_id': 'b442a580b9504ababf305bf2b4c49512',
    'degraded': False
}

lease_sample2 = {
    'status': None,
    'user_id': None,
    'name': 'lease-2',
    'end_date': '2030-06-30T18:00:00.000000',
    'reservations': [
        {
            'status': 'pending',
            'lease_id': '9bcfff36-872e-4f47-9abe-9a58a4f22038',
            'min': 1,
            'max': 1,
            'hypervisor_properties': '',
            'resource_id': '369c83cb-d3de-4e15-9e15-b74625cf9ee5',
            'resource_properties': '[">=", "$vcpus", "2"]',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'id': '1b05370e-d92a-452d-80db-89842666b604',
            'resource_type': 'physical:host',
            'missing_resources': False,
            'resources_changed': False
        }
    ],
    'created_at': '2017-06-27 15:00:00',
    'updated_at': None,
    'events': [
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'start_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2017-06-27T18:00:00.000000',
            'id': '0d81cdd7-9390-4d19-8acf-746bc8f0167d'
        },
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'end_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2030-06-30T18:00:00.000000',
            'id': 'b2ac8924-b6d1-46fe-b1a9-43d9d5c683cf'
        },
        {
            'status': 'UNDONE',
            'lease_id': '6ee55c78-ac52-41a6-99af-2d2d73bcc466',
            'event_type': 'before_end_lease',
            'created_at': '2017-06-27 15:00:00',
            'updated_at': None,
            'time': '2030-06-28T18:00:00.000000',
            'id': 'ba97b406-e721-47fe-9097-8ce6569f15d3'
        }
    ],
    'id': 'ef32abe8-a1f7-4c2f-b5f2-941428848230',
    'project_id': 'aa45f56901ef45ee95e3d211097c0ea3',
    'start_date': '2017-06-27T18:00:00.000000',
    'trust_id': 'b442a580b9504ababf305bf2b4c49512',
    'degraded': False
}

host_sample1 = {
    "status": None,
    "hypervisor_type": "QEMU",
    "created_at": "2017-10-01 12:00:00",
    "updated_at": None,
    "hypervisor_hostname": "compute-1",
    "memory_mb": 4096,
    "cpu_info": "{\"dummy\": \"true\"}",
    "vcpus": 1,
    "service_name": "blazar",
    "hypervisor_version": 2005000,
    "local_gb": 128,
    "id": "1",
    "trust_id": "dummy",
    "ex1": "dummy",
    "reservable": True
}

host_sample2 = {
    "status": None,
    "hypervisor_type": "QEMU",
    "created_at": "2017-10-01 12:00:00",
    "updated_at": None,
    "hypervisor_hostname": "compute-2",
    "memory_mb": 4096,
    "cpu_info": "{\"dummy\": \"true\"}",
    "vcpus": 1,
    "service_name": "blazar",
    "hypervisor_version": 2005000,
    "local_gb": 128,
    "id": "2",
    "trust_id": "dummy",
    "ex2": "dummy",
    "reservable": True
}


class DummyHypervisor(object):
    def __init__(self, host_name):
        self.hypervisor_hostname = host_name


hypervisor_sample1 = DummyHypervisor('compute-1')
hypervisor_sample2 = DummyHypervisor('compute-2')


def data(TEST):
    TEST.leases = utils.TestDataContainer()

    TEST.leases.add(api.client.Lease(lease_sample1))
    TEST.leases.add(api.client.Lease(lease_sample2))

    TEST.hosts = utils.TestDataContainer()

    TEST.hosts.add(api.client.Host(host_sample1))
    TEST.hosts.add(api.client.Host(host_sample2))

    TEST.hypervisors = utils.TestDataContainer()

    TEST.hypervisors.add(hypervisor_sample1)
    TEST.hypervisors.add(hypervisor_sample2)
