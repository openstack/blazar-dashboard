(function(window, horizon, $, undefined) {
  'use strict';

  var selector = undefined; // what selector determines the calendarElement
  var rowAttr = undefined; // what attribute from resources.json labels each chart row
  var pluralResourceType = undefined; // This resource type plural display name

  // Used for the chooser filter. Leave undefined for no filter
  var chooserAttr = undefined; // what attribute from resources.json should be used to categorize resources
  var chooserAttrPretty = undefined; // display name for chooserAttr
  var populateChooser = undefined; // a function that (partially) fills the resource category filter
  if ($('#blazar-calendar-host').length !== 0) {
    selector = '#blazar-calendar-host';
    rowAttr = "node_name";
    pluralResourceType = gettext("Hosts");
    chooserAttr = "node_type";
    chooserAttrPretty = gettext("Node Type");
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
    pluralResourceType = gettext("Networks")
    rowAttr = "segment_id";
  }
  if ($('#blazar-calendar-device').length !== 0) {
    selector = '#blazar-calendar-device'
    pluralResourceType = gettext("Devices")
    rowAttr = "device_name";

    chooserAttr = "vendor";
    chooserAttrPretty = gettext("Vendor");
    populateChooser = function(chooser, availableResourceTypes){}
  }
  if (selector == undefined) return;
  var calendarElement = $(selector);

  function init() {
    var chart; // The chart object
    var allReservations;
    var filteredReservations; // Reservations to show based on filter
    var form;
    var resources; // Used to calculate the height of the chart

    // Guard against re-running init() and a pointless calendar.json load.
    // Horizon seems to call us twice for some reason
    if (calendarElement.hasClass("loaded").length > 0) {
      console.log('blocking duplicate init');
    }
    calendarElement.addClass('loaded');

    $.getJSON("resources.json")
      .done(function(resp) {
        resources = resp.resources;
        var reservationsWithResources = resp.reservations;
        reservationsWithResources.forEach( function(reservation) {
          resp.resources.forEach(function(resource){
            if(reservation[rowAttr] == resource[rowAttr]){
              reservation[chooserAttr] = resource[chooserAttr]
            }
          })
        });
        var reservationsById = {}
        reservationsWithResources.forEach(function(reservation){
          if(!(reservation.id in reservationsById)){
            reservationsById[reservation.id] = reservation
            reservation.name = reservation.id
            reservation.data = []
          }
          var newReservation = {
            'start_date': new Date(reservation.start_date),
            'end_date': new Date(reservation.end_date),
            'x': reservation[rowAttr],
            'y': [
              new Date(reservation.start_date).getTime(),
              new Date(reservation.end_date).getTime()
            ],
          }
          newReservation[chooserAttr] = reservation[chooserAttr]
          reservationsById[reservation.id].data.push(newReservation)
        })
        // Dummy data to force rendering of all resources
        reservationsById["0"] = {"name": "0", "data": []}
        // For this row shows up at all, we need at least 1 data point.
        resp.resources.forEach(function(resource){
          var dummyData = {x: resource[rowAttr], y: [0, 0]}
          dummyData[chooserAttr] = resource[chooserAttr]
          reservationsById["0"].data.push(dummyData)
        })
        allReservations = Object.values(reservationsById)

        filteredReservations = allReservations;

        // populate resource-type-chooser
        var chooser = $("#resource-type-chooser");
        if(populateChooser != undefined){
          $("label[for='resource-type-chooser']").text(chooserAttrPretty);
          var availableResourceTypes = {};
          resp.resources.forEach(function(resource) {
              availableResourceTypes[resource[chooserAttr]] = true;
          });
          chooser.empty();
          chooser.append(new Option(`${gettext("All")} ${pluralResourceType}`, '*'));
          populateChooser(chooser, availableResourceTypes)
          Object.keys(availableResourceTypes).forEach(function (key) {
            chooser.append(new Option(key, key));
          });
          chooser.prop('disabled', false);
          chooser.change(function() {
            var chosenType = $('#resource-type-chooser').val();
            filteredReservations = allReservations.map(function (reservation) {
              var reservationCopy = Object.assign({}, reservation)
              reservationCopy.data = reservation.data.filter(function(resource){
                return chosenType === '*' || chosenType === resource[chooserAttr];
              })
              return reservationCopy
            })
            chart.updateOptions({series: filteredReservations})
            setTimeDomain(getTimeDomain())
          });
        } else {
          chooser.hide()
        }
        constructCalendar(filteredReservations, computeTimeDomain(7))
    })
    .fail(function() {
      calendarElement.html(`<div class="alert alert-danger">${gettext("Unable to load reservations")}.</div>`);
    });

    function constructCalendar(rows, timeDomain){
      calendarElement.empty();
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
            var resourcesReserved = datum.data.map(function(el){ return el.x }).join("<br>")
            return `<div class='tooltip-content'><dl>
              <dt>${gettext("Project")}</dt>
                <dd>${datum.project_id}</dd>
              <dt>${pluralResourceType}</dt>
                <dd>${resourcesReserved}</dd>
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
