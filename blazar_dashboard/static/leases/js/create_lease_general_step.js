(function (window, horizon, $, undefined) {
    'use strict';

    $('#id_start_date').datepicker({
      format: 'yyyy-mm-dd',
      todayHighlight: true,
      autoclose: true
    });

    $('#id_end_date').attr('readonly', 'readonly');

    var offset = new Date().getTimezoneOffset();
    var cookie_offset = $('#cookie_offset').val();

    if (cookie_offset != offset) {
      $('#timezone').show();
    } else {
      $('#timezone').hide();
    }

    $('#id_number_of_days, #id_start_date').on('change', function (event) {
      var numberOfDays = $('#id_number_of_days').val();
      if (numberOfDays != '' || $('#id_start_date').val() != '') {
        setEndDateTime();
      }
    });

    function setEndDateTime() {
      var startDate = $('#id_start_date').datepicker('getDate');
      if (startDate == 'Invalid Date') {
        startDate = new Date();
      }

      var leaseLength = parseInt($('#id_number_of_days').val());
      if (isNaN(leaseLength)) {
        $('#id_number_of_days').val('1');
        leaseLength = 1;
      }
      var result = new Date(startDate);
      result.setDate(result.getDate() + leaseLength);

      $('#id_end_date').val(formatDate(result));
    }

    function formatDate(date) {
      var d = new Date(date),
        month = '' + (d.getMonth() + 1),
        day = '' + d.getDate(),
        year = d.getFullYear();

      if (month.length < 2) month = '0' + month;
      if (day.length < 2) day = '0' + day;

      return [year, month, day].join('-');
    }

 })(window, horizon, jQuery);
