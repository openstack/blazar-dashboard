function setResourceTypeInput(resource_type) {
  var inputState = !$('#id_with_' + resource_type).prop('checked');
  $('.create-lease-switch-on-' + resource_type).each(function() {
      $(this).attr('disabled', inputState);
  });
};
