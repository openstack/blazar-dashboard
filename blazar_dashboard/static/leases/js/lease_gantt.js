(function(window, horizon, $, undefined) {
  'use strict';

  // don't run on other pages. the JS is loaded everywhere via the
  // ADD_JS_FILES directive in the .py file in enabled/
  var gantt_element = undefined;
  var resource_type = undefined;
  var selector = undefined;
  var task_attr = undefined;
  var populateChooser = undefined;
  if ($('#blazar-gantt').length !== 0) {
    gantt_element = $('#blazar-gantt');
    resource_type = "host";
    selector = '#blazar-gantt';
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

      chooser.empty(); // make idempotent so multiple loads don't fill multiple times (should also fix the multiple-load thing later...)
      chooser.append(new Option('All Nodes', '*'));
      nodeTypesPretty.forEach(function(nt) {
        if (availableResourceTypes[nt[0]]) {
          chooser.append(new Option(nt[1], nt[0]));
          delete availableResourceTypes[nt[0]];
        }
      });
      // fill chooser with node-types without a pretty name (when new ones pop up)
      Object.keys(availableResourceTypes).forEach(function (key) {
        if (availableResourceTypes[key]) {
          chooser.append(new Option(key, key));
        }
      });
      chooser.prop('disabled', false);
    }
  }
  if ($('#blazar-gantt-network').length !== 0) {
    gantt_element = $('#blazar-gantt-network');
    resource_type = "network";
    selector = '#blazar-gantt-network'
  }
  if ($('#blazar-gantt-device').length !== 0) {
    gantt_element = $('#blazar-gantt-device');
    resource_type = "device";
    selector = '#blazar-gantt-device'
  }
  if (gantt_element == undefined) return;

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
      return;
    }
    gantt_element.addClass('loaded');

    $.getJSON("resources.json")
    .done(function(resp) {

      all_tasks = resp.reservations.map(function(reservation, i) {
        reservation.resources = resp.reservations.filter(
          function(r) {
            return r.id === this.id;
          },
          reservation
        ).map(function(h) { return h[task_attr]; });

        return {
          'startDate': new Date(reservation.start_date),
          'endDate': new Date(reservation.end_date),
          'taskName': reservation[task_attr],
          'status': reservation.status,
          'data': reservation
        }
      });
      tasks = all_tasks;
      resources = resp.resources;

      // populate node-type-chooser
      var availableResourceTypes = {};
      resources.forEach(function(host) {
          availableResourceTypes[host.node_type] = true;
      });
      var chooser = $("#node-type-chooser");
      populateChooser(chooser, availableResourceTypes)

      var taskNames = $.map(resp.resources, function(host, i) {
        return host[task_attr];
      });
      /* set initial time range */
      var timeDomain = computeTimeDomain(7);

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
    })
    .fail(function() {
      gantt_element.html('<div class="alert alert-danger">Unable to load reservations.</div>');
    });

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

    $('#node-type-chooser').change(function() {
      var timeDomain = getTimeDomain();
      var nodeType = $('#node-type-chooser').val();

      var filteredTaskNames = resources
        .filter(function (host) {return nodeType === '*' || nodeType === host.node_type})
        .map(function (host) {return host.node_name});

      tasks = all_tasks.filter(function(task) {
        return filteredTaskNames.indexOf(task.taskName) >= 0
      });

      gantt_element.empty().height(20 * filteredTaskNames.length);
      gantt = d3.gantt({
        selector: selector,
        taskTypes: filteredTaskNames,
        taskStatus: taskStatus,
        tickFormat: format,
        timeDomainStart: timeDomain[0],
        timeDomainEnd: timeDomain[1],
      });
      console.log(tasks)
      gantt(tasks);
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
