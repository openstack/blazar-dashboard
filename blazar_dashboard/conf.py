from django.conf import settings

floatingip_reservation = (
    getattr(settings, 'OPENSTACK_BLAZAR_FLOATINGIP_RESERVATION', {}))
