from django.conf import settings

floatingip_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_FLOATINGIP_RESERVATION', {}))

device_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_DEVICE_RESERVATION',
            {'enabled': False}))
