from blazar_dashboard.api import client
from django.utils.translation import ugettext_lazy as _
import logging

logger = logging.getLogger(__name__)


def reservation_data(request, include_empty_option=False):
    """Returns a list of tuples of all reservations for a user.

    Generates a list of reservations available. And returns a list of
    (id, name) tuples.

    :param request: django http request object
    :param include_empty_option: flag to include a empty tuple in the front of
        the list
    :return: list of (id, name) tuples
    """

    leases = client.lease_list(request)
    reservations = []
    if leases:
        for l in leases:
            reservations += [(r['id'], '{} ({})'.format(l['name'], r['id']))
                             for r in l.reservations if r['status'] == 'active']

    if len(reservations) > 0:
        if include_empty_option:
            return [('', _('Select Reservation')), ] + reservations
        else:
            return reservations

    if include_empty_option:
        return [('', _('No Reservation Available')), ]
    return []
