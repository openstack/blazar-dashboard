============
Installation
============

Enabling in DevStack
====================

The DevStack plugin for Blazar automatically sets up blazar-dashboard if
Horizon is enabled, which is the case by default.

Manual Installation
===================

Begin by cloning the Horizon and Blazar dashboard repositories::

    git clone https://opendev.org/openstack/horizon
    git clone https://opendev.org/openstack/blazar-dashboard

Create a virtual environment and install Horizon dependencies::

    cd horizon
    tox -e runserver --notest

Set up your ``local_settings.py`` file::

    cp openstack_dashboard/local/local_settings.py.example openstack_dashboard/local/local_settings.py

Open up the copied ``local_settings.py`` file in your preferred text
editor. You will want to customize several settings:

-  ``OPENSTACK_HOST`` should be configured with the hostname of your
   OpenStack server. Verify that the ``OPENSTACK_KEYSTONE_URL`` and
   ``OPENSTACK_KEYSTONE_DEFAULT_ROLE`` settings are correct for your
   environment. (They should be correct unless you modified your
   OpenStack server to change them.)

Install Blazar dashboard with all dependencies in your virtual environment::

    .tox/runserver/bin/pip install -e ../blazar-dashboard/

And enable it in Horizon::

    ln -s /path/to/blazar-dashboard/blazar_dashboard/enabled/_90_project_reservations_panelgroup.py openstack_dashboard/local/enabled
    ln -s /path/to/blazar-dashboard/blazar_dashboard/enabled/_90_admin_reservation_panelgroup.py openstack_dashboard/local/enabled
    ln -s /path/to/blazar-dashboard/blazar_dashboard/enabled/_91_project_reservations_leases_panel.py openstack_dashboard/local/enabled
    ln -s /path/to/blazar-dashboard/blazar_dashboard/enabled/_91_admin_reservation_hosts_panel.py openstack_dashboard/local/enabled

Start horizon and it runs with the newly enabled Blazar dashboard.

Or to test the plugin run::

    tox -e runserver -- 0.0.0.0:8080

to have the application start on port 8080 and the horizon dashboard will be
available in your browser at http://localhost:8080/
