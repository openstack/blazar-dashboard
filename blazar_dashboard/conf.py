from django.conf import settings

host_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_HOST_RESERVATION', {
        'enabled': True,
    }))

floatingip_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_FLOATINGIP_RESERVATION', {
        'enabled': False, }))

network_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_NETWORK_RESERVATION', {
        'enabled': True,
    }))

device_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_DEVICE_RESERVATION', {
        'enabled': False,
    }))
