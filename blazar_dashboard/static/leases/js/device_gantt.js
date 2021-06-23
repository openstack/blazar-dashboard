(function(window, horizon, $, undefined) {
  'use strict';

  // don't run on other pages. the JS is loaded everywhere via the
  // ADD_JS_FILES directive in the .py file in enabled/
  if ($('#blazar-gantt-device').length === 0) return;

  function init() {
    var gantt;
    var all_tasks;
    var tasks;
    var devices;
    var form;

    var format = '%d-%b %H:%M';
    var taskStatus = {
      'active': 'task-active',
      'pending': 'task-pending'
    };

    // Guard against re-running init() and a pointless calendar.json load.
    // Horizon seems to call us twice for some reason
    if ($('#blazar-gantt-device.loaded').length > 0) {
      console.log('blocking duplicate init');
      return;
    }
    $('#blazar-gantt-device').addClass('loaded');

    $.getJSON('../device_calendar.json')
    .done(function(resp) {

      all_tasks = resp.reservations.map(function(reservation, i) {
        reservation.devices = resp.reservations.filter(
          function(r) {
            return r.id === this.id;
          },
          reservation
        ).map(function(d) { return d.name; });

        return {
          'startDate': new Date(reservation.start_date),
          'endDate': new Date(reservation.end_date),
          'taskName': reservation.name,
          'status': reservation.status,
          'data': reservation
        }
      });
      tasks = all_tasks;
      devices = resp.devices;

      var taskNames = $.map(resp.devices, function(device, i) {
        return device.name;
      });

      $('#blazar-gantt-device').empty().height(20 * taskNames.length);
      gantt = d3.gantt.device({
        selector: '#blazar-gantt-device',
        taskTypes: taskNames,
        taskStatus: taskStatus,
        tickFormat: format
      });
      gantt(tasks);

      /* set initial time range */
      setTimeDomain(gantt.timeDomain());
    })
    .fail(function() {
      $('#blazar-gantt-device').html('<div class="alert alert-danger">Unable to load reservations.</div>');
    });

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

    form = $('form[name="blazar-gantt-device-controls"]');

    $('input[data-datepicker]', form).datepicker({
      dateFormat: 'mm/dd/yyyy'
    });

    $('#node-type-chooser').change(function() {
      var timeDomain = getTimeDomain();

      var filteredTaskNames = devices
        .map(function (device) {return device.name});

      tasks = all_tasks.filter(function(task) {
        return filteredTaskNames.indexOf(task.taskName) >= 0
      });

      $('#blazar-gantt-device').empty().height(20 * filteredTaskNames.length);
      gantt = d3.gantt.device({
        selector: '#blazar-gantt-device',
        taskTypes: filteredTaskNames,
        taskStatus: taskStatus,
        tickFormat: format,
        timeDomainStart: timeDomain[0],
        timeDomainEnd: timeDomain[1],
      });
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
      var days = $(this).data("gantt-days");
      var padFraction = 1/8; // gantt chart default is 3 hours for 1 day
      var timeDomain = [
        d3.time.day.offset(Date.now(), -days * padFraction),
        d3.time.day.offset(Date.now(), days * (1 + padFraction))
      ];
      setTimeDomain(timeDomain);
      gantt.timeDomain(timeDomain);
      redraw();
    });
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
