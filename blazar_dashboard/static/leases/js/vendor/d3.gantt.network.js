/**
 * @author Dimitry Kudrayvtsev
 * @version 2.1
 */

d3.gantt.network = function(options) {

  var margin = {
    top: 20,
    right: 40,
    bottom: 20,
    left: 150
  };

  var timeDomainStart = options.timeDomainStart || d3.time.hour.offset(new Date(), -3);
  timeDomainStart.setMinutes(0, 0, 0);
  var timeDomainEnd = options.timeDomainEnd || d3.time.day.offset(timeDomainStart, +1);
  var taskTypes = options.taskTypes || [];
  var taskStatus = options.taskStatus || [];
  var selector = options.selector || '#d3-gantt-network';
  var el = document.querySelector(selector);
  var height = el.clientHeight - margin.top - margin.bottom - 5;
  var width = el.clientWidth - margin.right - margin.left - 5;
  var tickFormat = options.tickFormat || "%H:%M";

  var keyFunction = function(d) {
    return d.startDate + d.taskName + d.endDate;
  };

  var rectTransform = function(d) {
    return "translate(" + x(d.startDate) + "," + y(d.taskName) + ")";
  };

  var x;
  var y;
  var xAxis;
  var yAxis;
  var gridX;

  var tooltip = d3.select(selector).append("div").attr("class", "tooltip").style("opacity", 0);

  var makeXAxis = function makeXGrid() {
    return d3.svg.axis().scale(x).orient("bottom");
  };

  var makeYAxis = function makeYAxis() {
    return d3.svg.axis().scale(y).orient("left");
  };

  var initAxis = function() {
    x = d3.time.scale().domain([timeDomainStart, timeDomainEnd]).range([0, width]).clamp(true);
    y = d3.scale.ordinal().domain(taskTypes).rangeRoundBands([0, height - margin.top - margin.bottom], .1);
    xAxis = makeXAxis().tickFormat(d3.time.format(tickFormat));
    yAxis = makeYAxis().tickFormat(function(d) {
      return d;
    });
    gridX = makeXAxis().tickSize(-height + margin.top + margin.bottom, 0, 0).tickFormat('');
  };

  function tooltipContent(d) {
    var fmt = d3.time.format('%-m/%d/%Y at %-I:%M %p');
    return '<div class="tooltip-content"><dl><dt>Project</dt><dd>'
      + d.data.project_id
      + '</dd><dt>Name</dt><dd>'
      + d.data.name
      + '</dd><dt>Networks</dt><dd>'
      + d.data.networks.join('<br>')
      + '</dd><dt>Reserved</dt><dd>'
      + fmt(d.startDate) + ' <strong>to</strong><br/>' + fmt(d.endDate)
      + '</dd></dl></div>';
  }

  function gantt(tasks) {
    initAxis();

    var svg = d3.select(selector)
      .append("svg")
      .attr("class", "chart")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("class", "gantt-chart")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .attr("transform", "translate(" + margin.left + ", " + margin.top + ")");

    /* gridlines */
    svg.append('g')
      .attr('class', 'grid')
      .attr("transform", "translate(0," + (height - margin.top - margin.bottom) + ")")
      .call(gridX);

    /* now */
    var now = new Date();
    svg.append("line")
      .attr("class", "time-now")
      .attr("x1", x(now))
      .attr("y1", 0)
      .attr("x2", x(now))
      .attr("y2", height - margin.top - margin.bottom);

    /* reservation data */
    var colors = d3.scale.category20();

    var reservationColors = {};

    svg.selectAll(".chart")
      .data(tasks, keyFunction).enter()
      .append("rect")
      .attr("fill", function(d, i) {
        if (! reservationColors[d.data.id]) {
          reservationColors[d.data.id] = colors(Object.keys(reservationColors).length);
        }
        return reservationColors[d.data.id];
      })
      .attr("class", function(d) {
        var value = 'task task-' + d.data.id;

        if (taskStatus[d.status]) {
          value += ' task-' + d.status;
        }
        return value;
      })
      .attr("y", 0)
      .attr("transform", rectTransform)
      .attr("height", function(d) {
        return y.rangeBand();
      })
      .attr("width", function(d) {
        return (x(d.endDate) - x(d.startDate));
      })
      .on("mouseover", function(d) {
        d3.selectAll('.task-'+d.data.id).classed('task-hover', true);
        tooltip.transition().duration(200).style("opacity", 1);
        tooltip.html(tooltipContent(d))
          .style("left", (d3.event.offsetX) + "px")
          .style("top", (d3.event.offsetY) + "px");
      })
      .on("mouseout", function(d) {
        d3.selectAll('.task-'+d.data.id).classed('task-hover', false);
        tooltip
          .transition().duration(200).style("opacity", 0)
          .each("end", function() {
            tooltip.style("left", 0).style("top", 0).html('');
          });
      })
      .on("mousemove", function() {
        var w0 = d3.select('body').property('clientWidth');
        var w1 = tooltip.property('clientWidth');
        var pad = 25;
        var left;
        var top;
        if (d3.event.pageX + w1 < w0) {
          left = d3.event.offsetX + pad;
          top = d3.event.offsetY - pad;
        } else {
          left = d3.event.offsetX - w1 - pad;
          top = d3.event.offsetY - pad;
        }
        tooltip.style("left", left + "px").style("top", top + "px");
      });

    /* axes */
    svg.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0, " + (height - margin.top - margin.bottom) + ")")
      .transition()
      .call(xAxis);

    svg.append("g").attr("class", "y axis").transition().call(yAxis);

    return gantt;

  };

  gantt.redraw = function(tasks) {
    height = el.clientHeight - margin.top - margin.bottom - 5;
    width = el.clientWidth - margin.right - margin.left - 5;

    initAxis();

    var svg = d3.select("svg");

    /* gridlines */
    svg.select('.grid').transition().call(gridX);

    /* now */
    var now = new Date();
    svg.select(".time-now").transition()
      .attr("x1", x(now))
      .attr("x2", x(now));

    /* data */
    var ganttChartGroup = svg.select(".gantt-chart");
    var rect = ganttChartGroup.selectAll("rect").data(tasks, keyFunction);

    rect.enter()
      .insert("rect", ":first-child")
      .attr("class", function(d) {
        if (taskStatus[d.status] == null) {
          return "task";
        }
        return taskStatus[d.status];
      })
      .transition()
      .attr("y", 0)
      .attr("transform", rectTransform)
      .attr("height", function(d) {
        return y.rangeBand();
      })
      .attr("width", function(d) {
        return (x(d.endDate) - x(d.startDate));
      });

    rect.transition()
      .attr("transform", rectTransform)
      .attr("height", function(d) {
        return y.rangeBand();
      })
      .attr("width", function(d) {
        return (x(d.endDate) - x(d.startDate));
      });

    rect.exit().remove();

    /* axes */
    svg.select(".x").transition().call(xAxis);
    svg.select(".y").transition().call(yAxis);

    return gantt;
  };

  gantt.margin = function(value) {
    if (!arguments.length)
      return margin;
    margin = value;
    return gantt;
  };

  gantt.timeDomain = function(value) {
    if (!arguments.length)
      return [timeDomainStart, timeDomainEnd];
    timeDomainStart = +value[0];
    timeDomainEnd = +value[1];
    return gantt;
  };

  gantt.taskTypes = function(value) {
    if (!arguments.length)
      return taskTypes;
    taskTypes = value;
    return gantt;
  };

  gantt.taskStatus = function(value) {
    if (!arguments.length)
      return taskStatus;
    taskStatus = value;
    return gantt;
  };

  gantt.width = function(value) {
    if (!arguments.length)
      return width;
    width = +value;
    return gantt;
  };

  gantt.height = function(value) {
    if (!arguments.length)
      return height;
    height = +value;
    return gantt;
  };

  gantt.tickFormat = function(value) {
    if (!arguments.length)
      return tickFormat;
    tickFormat = value;
    return gantt;
  };

  return gantt;
};
