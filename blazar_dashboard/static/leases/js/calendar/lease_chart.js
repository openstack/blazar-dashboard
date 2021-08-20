(function(window, horizon, $, undefined) {
  'use strict';

  const CHART_TITLE_HEIGHT = 68;
  const ROW_HEIGHT = 60;

  const selector = '#blazar-calendar-host';
  const pluralResourceType = gettext("Hosts");
  if ($(selector).length < 1) return;
  const calendarElement = $(selector);
  const form = $('form[name="blazar-calendar-controls"]');

  function init() {
    calendarElement.addClass('loaded');
    $.getJSON("resources.json")
      .done(function(resp) {
        const rowAttr = resp.row_attr;
        // For this row shows up at all, we need at least 1 data point.
        const reservationsById = {}
        resp.reservations.forEach(function(reservation){
          if(!(reservation.reservation_id in reservationsById)){
            reservationsById[reservation.reservation_id] = reservation
            reservation.name = reservation.reservation_id
            reservation.data = []
          }
          const newReservation = {
            'start_date': new Date(reservation.start_date),
            'end_date': new Date(reservation.end_date),
            'x': reservation[rowAttr],
            'y': [
              new Date(reservation.start_date).getTime(),
              new Date(reservation.end_date).getTime()
            ],
          }
          reservationsById[reservation.reservation_id].data.push(newReservation)
        })
        reservationsById["0"] = {"name": "0", "data": []}
        resp.resources.forEach(function(resource){
          reservationsById["0"].data.push({x: resource[rowAttr], y: [0, 0]})
        })
        const allReservations = Object.values(reservationsById)
        constructCalendar(allReservations, computeTimeDomain(7), resp.resources)
    })
    .fail(function() {
      calendarElement.html(`<div class="alert alert-danger">${gettext("Unable to load reservations")}.</div>`);
    });

    function constructCalendar(rows, timeDomain, resources){
      calendarElement.empty();
      const options = {
        series: rows,
        chart: {
          type: 'rangeBar',
          toolbar: {show: false},
          zoom: {enabled: false, type: 'xy'},
          height: ROW_HEIGHT * resources.length + CHART_TITLE_HEIGHT,
          width: "100%",
        },
        plotOptions: { bar: {horizontal: true, rangeBarGroupRows: true}},
        xaxis: { type: 'datetime' },
        legend: { show: false },
        tooltip: {
          custom: function({series, seriesIndex, dataPointIndex, w}) {
            const datum = rows[seriesIndex];
            const resourcesReserved = datum.data.map(function(el){ return el.x }).join("<br>");
            const project_dt = "";
            if(datum.project_id){
              project_dt = `<dt>${gettext("Project")}</dt>
                <dd>${datum.project_id}</dd>`;
            }
            return `<div class='tooltip-content'><dl>
              ${project_dt}
              <dt>${pluralResourceType}</dt>
                <dd>${resourcesReserved}</dd>
              <dt>${gettext("Reserved")}</dt>
                <dd>${datum.start_date} <strong>${gettext("to")}</strong> ${datum.end_date}</dd>
            </dl></div>`;
          }
        },
        annotations: {
          xaxis: [
            {
              x: new Date().getTime(),
              borderColor: '#00E396',
            }
          ]
        },
      }
      const chart = new ApexCharts(document.querySelector(selector), options);
      chart.render();

      setTimeDomain(timeDomain, chart); // Also sets the yaxis limits

      $('input[data-datepicker]', form).datepicker({
        dateFormat: 'mm/dd/yyyy'
      });

      $('input', form).on('change', function() {
        if (form.hasClass('time-domain-processed')) {
          const timeDomain = getTimeDomain();
          // If invalid ordering is chosen, set period to 1 day
          if (timeDomain[0] >= timeDomain[1]) {
            timeDomain[1] = d3.time.day.offset(timeDomain[0], +1);
          }
          setTimeDomain(timeDomain, chart);
        }
      });

      $('.calendar-quickdays').click(function() {
        const days = parseInt($(this).data("calendar-days"));
        if (!isNaN(days)) {
          const timeDomain = computeTimeDomain(days);
          setTimeDomain(timeDomain, chart);
        }
      })
    }

    function computeTimeDomain(days) {
      const padFraction = 1/8; // chart default is 3 hours for 1 day
      return [
        d3.time.day.offset(Date.now(), -days * padFraction),
        d3.time.day.offset(Date.now(), days * (1 + padFraction))
      ];
    }

    function setTimeDomain(timeDomain, chart) {
      // Set the input elements
      form.removeClass('time-domain-processed');
      $('#dateStart').datepicker('setDate', timeDomain[0]);
      $('#timeStartHours').val(timeDomain[0].getHours());
      $('#dateEnd').datepicker('setDate', timeDomain[1]);
      $('#timeEndHours').val(timeDomain[1].getHours());
      form.addClass('time-domain-processed');
      const options = { yaxis: {min: timeDomain[0].getTime(), max: timeDomain[1].getTime()}}
      chart.updateOptions(options)
    }

    function getTimeDomain() {
      const timeDomain = [
        $('#dateStart').datepicker('getDate'),
        $('#dateEnd').datepicker('getDate')
      ];

      timeDomain[0].setHours($('#timeStartHours').val());
      timeDomain[0].setMinutes(0);
      timeDomain[1].setHours($('#timeEndHours').val());
      timeDomain[1].setMinutes(0);

      return timeDomain;
    }
  }

  horizon.addInitFunction(init);

})(window, horizon, jQuery);
