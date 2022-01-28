==============================
Resource Availability Calendar
==============================

Blazar Dashboard features a resource availability calendar that displays a
timeline of resources, showing when each resource is reserved.

Currently, physical hosts are the only supported resource type.

Configuration
=============
In the Horizon settings, the option ``OPENSTACK_BLAZAR_HOST_RESERVATION`` can
be configured.

.. sourcecode::

    OPENSTACK_BLAZAR_HOST_RESERVATION = {
        'enabled': True,
        'calendar_attribute': 'hypervisor_hostname',
    }

..

If ``enabled`` is ``True``, the host calendar will be enabled. The option
``calendar_attribute`` is used to label each row of the calendar. By default,
it uses the ``hypervisor_hostname`` attribute of a host. If the host has
resource properties set, they could also be used.

In order to be able to view the calendar, a user needs permission for
``blazar:oshosts:get`` and ``blazar:oshosts:get_allocations``.
