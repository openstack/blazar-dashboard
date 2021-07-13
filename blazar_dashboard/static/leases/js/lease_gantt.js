(function(window, horizon, $, undefined) {
  'use strict';

  var selector = undefined; // what selector determines the gantt_element
  var task_attr = undefined; // what attribute from resources.json labels each chart row
  var plural_resource_type = undefined; // This resource type plural display name

  // Used for the chooser filter. Leave undefined for no filter
  var resource_type_attr = undefined; // what attribute from resources.json should be used to categorize resources
  var resource_type_pretty = undefined; // display name for resource_type_attr
  var populateChooser = undefined; // a function that (partially) fills the resource category filter
  var filterTaskNames = function(resources, nodeType){return []}; // a function that filters tasks based on the chooser value
  if ($('#blazar-gantt-host').length !== 0) {
    selector = '#blazar-gantt-host';
    resource_type_attr = "node_type";
    resource_type_pretty = "Node Type";
    plural_resource_type = "Hosts";
    task_attr = "node_name";
    populateChooser = function(chooser, availableResourceTypes){
      var nodeTypesPretty = [ // preserve order so it's not random
        ['compute', 'Compute Node'],
        ['storage', 'Storage'],
        ['gpu_k80', 'GPU (K80)'],
        ['gpu_m40', 'GPU (M40)'],
        ['gpu_p100', 'GPU (P100)'],
        ['gpu_p100_nvlink', 'GPU (P100 + NVLink)'],
        ['gpu_p100_v100', 'GPU (P100 + V100)'],
        ['compute_cascadelake', 'Cascade Lake'],
        ['compute_cascadelake_r', 'Cascade Lake R'],
        ['compute_skylake', 'Skylake'],
        ['compute_haswell', 'Haswell'],
        ['compute_haswell_ib', 'Haswell + Infiniband Support'],
        ['compute_ib', 'Infiniband Support'],
        ['storage_hierarchy', 'Storage Hierarchy'],
        ['fpga', 'FPGA'],
        ['lowpower_xeon', 'Low power Xeon'],
        ['atom', 'Atom'],
        ['arm64', 'ARM64'],
      ];
      chooser.append(new Option('All Nodes', '*'));
      nodeTypesPretty.forEach(function(nt) {
        if (availableResourceTypes[nt[0]]) {
          chooser.append(new Option(nt[1], nt[0]));
          delete availableResourceTypes[nt[0]];
        }
      });
    }
    filterTaskNames = function(resources, nodeType){
      return resources
        .filter(function (host) {return nodeType === '*' || nodeType === host.node_type})
        .map(function (host) {return host.node_name});
    }
  }
  if ($('#blazar-gantt-network').length !== 0) {
    selector = '#blazar-gantt-network'
    plural_resource_type = "Networks"
    task_attr = "segment_id";
  }
  if ($('#blazar-gantt-device').length !== 0) {
    selector = '#blazar-gantt-device'
    resource_type_attr = "vendor";
    resource_type_pretty = "Vendor";
    task_attr = "device_name";
    populateChooser = function(chooser, availableResourceTypes){
      chooser.append(new Option('All Vendors', '*'));
    }
    plural_resource_type = "Devices"
    filterTaskNames = function(resources, nodeType){
      return resources
        .filter(function (device) {return nodeType === '*' || nodeType === device.vendor})
        .map(function (device) {return device.device_name});
    }
  }
  if (selector == undefined) return;
  var gantt_element = $(selector);

  function init() {
    var gantt;
    var all_tasks;
    var tasks;
    var resources;
    var form;

    var format = '%d-%b %H:%M';
    var taskStatus = {
      'active': 'task-active',
      'pending': 'task-pending'
    };

    // Guard against re-running init() and a pointless calendar.json load.
    // Horizon seems to call us twice for some reason
    if (gantt_element.hasClass("loaded").length > 0) {
      console.log('blocking duplicate init');
    }
    gantt_element.addClass('loaded');

    $.getJSON("resources.json")
    .done(function(resp) {
      all_tasks = resp.reservations.map(function(reservation, i) {
        reservation.resources = resp.reservations
          .filter( function(r) { return r.id === reservation.id; })
          .map(function(r) { return r[task_attr]; });

        return {
          'startDate': new Date(reservation.start_date),
          'endDate': new Date(reservation.end_date),
          'taskName': reservation[task_attr],
          'status': reservation.status,
          'data': reservation,
          'resource_type': plural_resource_type
        }
      });
      tasks = all_tasks;
      resources = resp.resources;

      // populate node-type-chooser
      var chooser = $("#resource-type-chooser");
      if(populateChooser != undefined){
        $("label[for='resource-type-chooser']").text(resource_type_pretty);
        var availableResourceTypes = {};
        resources.forEach(function(resource) {
            availableResourceTypes[resource[resource_type_attr]] = true;
        });
        chooser.empty();
        populateChooser(chooser, availableResourceTypes)
        Object.keys(availableResourceTypes).forEach(function (key) {
          if (availableResourceTypes[key]) {
            chooser.append(new Option(key, key));
          }
        });
        chooser.prop('disabled', false);
        chooser.change(function() {
          var timeDomain = getTimeDomain();
          var nodeType = $('#resource-type-chooser').val();
          var filteredTaskNames = filterTaskNames(resources, nodeType);
          tasks = all_tasks.filter(function(task) {
            return filteredTaskNames.includes(task.taskName)
          });
          construct_gantt(tasks, filteredTaskNames, timeDomain)
        });
      } else {
        chooser.hide()
      }

      var taskNames = $.map(resp.resources, function(resource, i) {
        return resource[task_attr];
      });

      /* set initial time range */
      var timeDomain = computeTimeDomain(7);

      construct_gantt(tasks, taskNames, timeDomain)
    })
    .fail(function() {
      gantt_element.html('<div class="alert alert-danger">Unable to load reservations.</div>');
    });

    function construct_gantt(tasks, taskNames, timeDomain){
      gantt_element.empty().height(20 * taskNames.length);
      gantt = d3.gantt({
        selector: selector,
        taskTypes: taskNames,
        taskStatus: taskStatus,
        tickFormat: format,
        timeDomainStart: timeDomain[0],
        timeDomainEnd: timeDomain[1]
      });
      gantt(tasks);
      setTimeDomain(timeDomain);
    }

    function computeTimeDomain(days) {
      var padFraction = 1/8; // gantt chart default is 3 hours for 1 day
      return [
        d3.time.day.offset(Date.now(), -days * padFraction),
        d3.time.day.offset(Date.now(), days * (1 + padFraction))
      ];
    }

    function setTimeDomain(timeDomain) {
      form.removeClass('time-domain-processed');
      $('#dateStart').datepicker('setDate', timeDomain[0]);
      $('#timeStartHours').val(timeDomain[0].getHours());
      $('#dateEnd').datepicker('setDate', timeDomain[1]);
      $('#timeEndHours').val(timeDomain[1].getHours());
      form.addClass('time-domain-processed');
    }

    function getTimeDomain() {
      var timeDomain = [
        $('#dateStart').datepicker('getDate'),
        $('#dateEnd').datepicker('getDate')
      ];

      timeDomain[0].setHours($('#timeStartHours').val());
      timeDomain[0].setMinutes(0);
      timeDomain[1].setHours($('#timeEndHours').val());
      timeDomain[1].setMinutes(0);

      return timeDomain;
    }

    function redraw() {
      if (gantt && tasks) {
        gantt.redraw(tasks);
      }
    }

    $(window).on('resize', redraw);

    form = $('form[name="blazar-gantt-controls"]');

    $('input[data-datepicker]', form).datepicker({
      dateFormat: 'mm/dd/yyyy'
    });

    $('input', form).on('change', function() {
      if (form.hasClass('time-domain-processed')) {
        var timeDomain = getTimeDomain();
        if (timeDomain[0] >= timeDomain[1]) {
          timeDomain[1] = d3.time.day.offset(timeDomain[0], +1);
          setTimeDomain(timeDomain);
        }
        gantt.timeDomain(timeDomain);
        redraw();
      }
    });

    $('.gantt-quickdays').click(function() {
      var days = parseInt($(this).data("gantt-days"));
      if (!isNaN(days)) {
        var timeDomain = computeTimeDomain(days);
        setTimeDomain(timeDomain);
        gantt.timeDomain(timeDomain);
        redraw();
      }
    });
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
