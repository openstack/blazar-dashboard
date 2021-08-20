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

from django.conf import settings

host_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_HOST_RESERVATION', {
        'enabled': True,
        'calendar_attribute': 'hypervisor_hostname',
    }))

floatingip_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_FLOATINGIP_RESERVATION', {
        'enabled': False, }))
