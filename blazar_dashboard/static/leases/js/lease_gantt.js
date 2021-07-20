(function(window, horizon, $, undefined) {
  'use strict';

  var selector = undefined; // what selector determines the calendar_element
  var row_attr = undefined; // what attribute from resources.json labels each chart row
  var plural_resource_type = undefined; // This resource type plural display name

  // Used for the chooser filter. Leave undefined for no filter
  var chooser_attr = undefined; // what attribute from resources.json should be used to categorize resources
  var chooser_attr_pretty = undefined; // display name for chooser_attr
  var populateChooser = undefined; // a function that (partially) fills the resource category filter
  if ($('#blazar-calendar-host').length !== 0) {
    selector = '#blazar-calendar-host';
    row_attr = "node_name";
    plural_resource_type = gettext("Hosts");
    chooser_attr = "node_type";
    chooser_attr_pretty = gettext("Node Type");
    populateChooser = function(chooser, availableResourceTypes){
      var nodeTypesPretty = [ // preserve order so it's not random
        ['compute', gettext('Compute Node')],
        ['storage', gettext('Storage')],
        ['gpu_k80', gettext('GPU (K80)')],
        ['gpu_m40', gettext('GPU (M40)')],
        ['gpu_p100', gettext('GPU (P100)')],
        ['gpu_p100_nvlink', gettext('GPU (P100 + NVLink)')],
        ['gpu_p100_v100', gettext('GPU (P100 + V100)')],
        ['compute_cascadelake', gettext('Cascade Lake')],
        ['compute_cascadelake_r', gettext('Cascade Lake R')],
        ['compute_skylake', gettext('Skylake')],
        ['compute_haswell', gettext('Haswell')],
        ['compute_haswell_ib', gettext('Haswell + Infiniband Support')],
        ['compute_ib', gettext('Infiniband Support')],
        ['storage_hierarchy', gettext('Storage Hierarchy')],
        ['fpga', gettext('FPGA')],
        ['lowpower_xeon', gettext('Low power Xeon')],
        ['atom', gettext('Atom')],
        ['arm64', gettext('ARM64')],
      ];
      nodeTypesPretty.forEach(function(nt) {
        if (availableResourceTypes[nt[0]]) {
          chooser.append(new Option(nt[1], nt[0]));
          delete availableResourceTypes[nt[0]];
        }
      });
    }
  }
  if ($('#blazar-calendar-network').length !== 0) {
    selector = '#blazar-calendar-network'
    plural_resource_type = gettext("Networks")
    row_attr = "segment_id";
  }
  if ($('#blazar-calendar-device').length !== 0) {
    selector = '#blazar-calendar-device'
    plural_resource_type = gettext("Devices")
    row_attr = "device_name";

    chooser_attr = "vendor";
    chooser_attr_pretty = gettext("Vendor");
    populateChooser = function(chooser, availableResourceTypes){}
  }
  if (selector == undefined) return;
  var calendar_element = $(selector);

  function init() {
    var chart; // The chart object
    var all_reservations;
    var filtered_reservations; // Reservations to show based on filter
    var form;
    var resources; // Used to calculate the height of the chart

    // Guard against re-running init() and a pointless calendar.json load.
    // Horizon seems to call us twice for some reason
    if (calendar_element.hasClass("loaded").length > 0) {
      console.log('blocking duplicate init');
    }
    calendar_element.addClass('loaded');

    $.getJSON("resources.json")
      .done(function(resp) {
        resources = resp.resources;
        var reservations_with_resources = resp.reservations;
        reservations_with_resources.forEach( function(reservation) {
          resp.resources.forEach(function(resource){
            if(reservation[row_attr] == resource[row_attr]){
              reservation[chooser_attr] = resource[chooser_attr]
            }
          })
        });
        var reservations_by_id = {}
        reservations_with_resources.forEach(function(reservation){
          if(!(reservation.id in reservations_by_id)){
            reservations_by_id[reservation.id] = reservation
            reservation.name = reservation.id
            reservation.data = []
          }
          var new_reservation = {
            'startDate': new Date(reservation.start_date),
            'endDate': new Date(reservation.end_date),
            'x': reservation[row_attr],
            'y': [
              new Date(reservation.start_date).getTime(),
              new Date(reservation.end_date).getTime()
            ],
          }
          new_reservation[chooser_attr] = reservation[chooser_attr]
          reservations_by_id[reservation.id].data.push(new_reservation)
        })
        // Dummy data to force rendering of all resources
        reservations_by_id["0"] = {"name": "0", "data": []}
        // For this row shows up at all, we need at least 1 data point.
        resp.resources.forEach(function(resource){
          var dummy_data = {x: resource[row_attr], y: [0, 0]}
          dummy_data[chooser_attr] = resource[chooser_attr]
          reservations_by_id["0"].data.push(dummy_data)
        })
        all_reservations = Object.values(reservations_by_id)

        filtered_reservations = all_reservations;

        // populate resource-type-chooser
        var chooser = $("#resource-type-chooser");
        if(populateChooser != undefined){
          $("label[for='resource-type-chooser']").text(chooser_attr_pretty);
          var availableResourceTypes = {};
          resp.resources.forEach(function(resource) {
              availableResourceTypes[resource[chooser_attr]] = true;
          });
          chooser.empty();
          chooser.append(new Option(`${gettext("All")} ${plural_resource_type}`, '*'));
          populateChooser(chooser, availableResourceTypes)
          Object.keys(availableResourceTypes).forEach(function (key) {
            chooser.append(new Option(key, key));
          });
          chooser.prop('disabled', false);
          chooser.change(function() {
            var chosen_type = $('#resource-type-chooser').val();
            filtered_reservations = all_reservations.map(function (reservation) {
              var reservation_copy = Object.assign({}, reservation)
              reservation_copy.data = reservation.data.filter(function(resource){
                return chosen_type === '*' || chosen_type === resource[chooser_attr];
              })
              return reservation_copy
            })
            chart.updateOptions({series: filtered_reservations})
            setTimeDomain(getTimeDomain())
          });
        } else {
          chooser.hide()
        }
        construct_calendar(filtered_reservations, computeTimeDomain(7))
    })
    .fail(function() {
      calendar_element.html(`<div class="alert alert-danger">${gettext("Unable to load reservations")}.</div>`);
    });

    function construct_calendar(rows, timeDomain){
      calendar_element.empty();
      var options = {
        series: rows,
        chart: {
          type: 'rangeBar',
          toolbar: {show: false},
          zoom: {enabled: false, type: 'xy'},
          height: 60 * resources.length,
          width: "100%",
        },
        plotOptions: { bar: {horizontal: true, rangeBarGroupRows: true}},
        xaxis: { type: 'datetime' },
        legend: { show: false },
        tooltip: {
          custom: function({series, seriesIndex, dataPointIndex, w}) {
            var datum = rows[seriesIndex]
            var resources_reserved = datum.data.map(function(el){ return el.x }).join("<br>")
            return `<div class='tooltip-content'><dl>
              <dt>${gettext("Project")}</dt>
                <dd>${datum.project_id}</dd>
              <dt>${plural_resource_type}</dt>
                <dd>${resources_reserved}</dd>
              <dt>${gettext("Reserved")}</dt>
                <dd>${datum.start_date} <strong>${gettext("to")}</strong> ${datum.end_date}</dd>
            </dl></div>`
          }
        },
        annotations: {
          xaxis: [
            {
              x: new Date().getTime(),
              borderColor: '#00E396',
            }
          ]
        }
      }
      chart = new ApexCharts(document.querySelector(selector), options);
      chart.render();
      setTimeDomain(timeDomain); // Also sets the yaxis limits
    }

    function computeTimeDomain(days) {
      var padFraction = 1/8; // chart default is 3 hours for 1 day
      return [
        d3.time.day.offset(Date.now(), -days * padFraction),
        d3.time.day.offset(Date.now(), days * (1 + padFraction))
      ];
    }

    function setTimeDomain(timeDomain) {
      // Set the input elements
      form.removeClass('time-domain-processed');
      $('#dateStart').datepicker('setDate', timeDomain[0]);
      $('#timeStartHours').val(timeDomain[0].getHours());
      $('#dateEnd').datepicker('setDate', timeDomain[1]);
      $('#timeEndHours').val(timeDomain[1].getHours());
      form.addClass('time-domain-processed');
      // If the chart exists, update its axis
      if(chart){
        var options = { yaxis: {min: timeDomain[0].getTime(), max: timeDomain[1].getTime()}}
        chart.updateOptions(options)
      }
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

    form = $('form[name="blazar-calendar-controls"]');

    $('input[data-datepicker]', form).datepicker({
      dateFormat: 'mm/dd/yyyy'
    });

    $('input', form).on('change', function() {
      if (form.hasClass('time-domain-processed')) {
        var timeDomain = getTimeDomain();
        // If invalid ordering is chosen, set period to 1 day
        if (timeDomain[0] >= timeDomain[1]) {
          timeDomain[1] = d3.time.day.offset(timeDomain[0], +1);
        }
        setTimeDomain(timeDomain);
      }
    });

    $('.calendar-quickdays').click(function() {
      var days = parseInt($(this).data("calendar-days"));
      if (!isNaN(days)) {
        var timeDomain = computeTimeDomain(days);
        setTimeDomain(timeDomain);
      }
    });
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
