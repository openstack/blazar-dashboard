import datetime

from django.forms.widgets import Widget
from django.template import loader
from django.utils.safestring import mark_safe


class TimespanWidget(Widget):
    """
    Produces 4 text boxes for days/hours/minutes/seconds. Converts data into
     - an empty string (net time is zero),
     - a string of the form "<integer>s", or
     - "invalid" if a non-numeric value is entered into one of the boxes.
    """
    template_name = 'project/leases/_widget_timespan.html'

    def get_context(self, name, value, attrs=None):
        return {'widget': {
            'name': name,
            'value': value,
        }}

    def render(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)

    def value_from_datadict(self, data, files, name):
        parts = {p: 0 for p in ['days', 'hours', 'minutes']}
        for part in parts:
            try:
                parts[part] = data['timespan-{}-{}'.format(name, part)]
            except LookupError:
                parts[part] = 0
                continue # missing assume 0

            if not parts[part]:
                # might be empty string
                parts[part] = 0
                continue

            try:
                parts[part] = float(parts[part])
            except ValueError:
                return 'invalid'

        timespan = datetime.timedelta(**parts)
        total_seconds = timespan.total_seconds()
        if abs(total_seconds) < 1:
            # if zero or sub-second time, ignore
            return ''
        return '{:.0f}s'.format(total_seconds)
