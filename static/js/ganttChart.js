const tooltip = d3.select(".ganttContainer")
  .append("div")
  .style("position", "absolute")
  .style("display", "none")
  .style("background", "white")
  .style("border", "1px solid #ccc")
  .style("border-radius", "4px")
  .style("padding", "6px 10px")
  .style("font-size", "13px")
  .style("pointer-events", "none")
  .style("z-index", "9999");

let tooltipContent = (d) => {
  let text = `
  <b>${d.person__name_canonical}</b>
  <br>${d.start.getFullYear()} → ${d.end.getFullYear()}
  <br>Current age: ${new Date().getFullYear() - d.birthdate.getFullYear()}
  `
  if (d.court__selection_type == "appointment") {
    text +=   `
  <br>Selection method: ${d.court__selection_method}
  <br>Appointed by: ${d.appointer_name} (${d.appointer_party})
  <br>Age at appointment: ${d.start.getFullYear() - d.birthdate.getFullYear()}
  `
  }
  else if (d.court__selection_type == "partisan election") {
    text +=   `
  <br>Selection method: ${d.court__selection_method}
  <br>Ticket party: ${d.ticket_party}
  <br>Age at election: ${d.start.getFullYear() - d.birthdate.getFullYear()}
  `
  }
  else if (d.court__selection_type == "nonpartisan election") {
    text +=   `
  <br>Selection method: ${d.court__selection_method}
  <br>Age at election: ${d.start.getFullYear() - d.birthdate.getFullYear()}
  `
  }
  return text
}

let tooltipContentRemaining = (d) => {
  return `
  <b>${d.person__name_canonical}</b>
  <br>${d.start.getFullYear()} → ${d.end.getFullYear()}
  <br>Selection method: ${d.court__selection_method}
  <br>Current age: ${new Date().getFullYear() - d.birthdate.getFullYear()}
  <br>Age at end of current term: ${d.end.getFullYear() - d.birthdate.getFullYear()}
  `
}

function makeGanttChart(data, selector) {
  const width  = 800
  const height = 50 * data.length
  const margin = { top: 20, right: 30, bottom: 40, left: 150 }

  const innerWidth  = width  - margin.left - margin.right;
  const innerHeight = height - margin.top  - margin.bottom;

  const parseDate = d3.timeParse("%Y-%m-%d");
  const parsed = data.map(d => ({
    ...d,
    start: d.start_date instanceof Date ? d.start_date : parseDate(d.start_date),
    end:   d.end_date   instanceof Date ? d.end_date   : parseDate(d.end_date),
    birthdate: d.person__birth_date instanceof Date ? d.person__birth_date   : parseDate(d.person__birth_date),
    party: d.court__selection_type == "appointment" ? d.appointer_party : d.court__selection_type == "partisan election" ? d.ticket_party : null
  }));

  console.log(parsed)

  const today = Date.now()

  // --- Scales ---
  const xScale = d3.scaleTime()
    .domain([
      d3.min(parsed, d => d.start),
      d3.max(parsed, d => d.end),
    ])
    .range([0, innerWidth]);

  const yScale = d3.scaleBand()
    .domain(parsed.map(d => d.person__name_canonical))
    .range([0, innerHeight])
    .padding(0.2);

  const colorToDate = d3.scaleOrdinal(
    // observable10 colors
    ["R", "Republican", "D", "Democratic", "I", null], ["#d62728", "#d62728", "#1f77b4", "#1f77b4", "#ff7f0e", "#7f7f7f"]
  )

  const colorRemaining = d3.scaleOrdinal(
    // category20 colors
    ["R", "Republican", "D", "Democratic", "I", null], ["#ff9896", "#ff9896", "#aec7e8", "#aec7e8", "#ffbb78", "#c7c7c7"]
  )

  // --- SVG setup ---
  const svg = d3.select(selector)
    .append("svg")
    .attr("width",  width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // --- Axes ---
  svg.append("g")
    .call(d3.axisLeft(yScale));

  svg.append("g")
    .attr("transform", `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).ticks(6).tickFormat(d3.timeFormat("%Y")));

  // --- Bars ---
    svg.selectAll(".bar")
    .data(parsed)
    .join("rect")
      .attr("class", "bar")
      .attr("y",      d => yScale(d.person__name_canonical))
      .attr("height", yScale.bandwidth())
      .attr("x",      d => xScale(d.start))
      .attr("width",  d => xScale(d.end) - xScale(d.start))
      .attr("opacity",   0)
      //.attr("rx",     3)

  svg.selectAll(".bar-to-date")
    .data(parsed)
    .join("rect")
      .attr("class", "bar-to-date")
      .attr("y",      d => yScale(d.person__name_canonical))
      .attr("height", yScale.bandwidth())
      .attr("x",      d => xScale(d.start))
      .attr("width",  d => xScale(new Date()) - xScale(d.start))
      .attr("fill",   d => colorToDate(d.party))
      //.attr("rx",     3)
      .on("mouseover", (event, d) => {
        tooltip
        .style("display", "block")
        .style("left", event.pageX + 10 + "px")
        .style("top",  event.pageY - 20 + "px")
        .html(tooltipContent(d));
        })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.pageX + 12 + "px")
          .style("top",  event.pageY - 28 + "px");
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      });

  svg.selectAll(".bar-remaining")
    .data(parsed)
    .join("rect")
      .attr("class", "bar-remaining")
      .attr("y",      d => yScale(d.person__name_canonical))
      .attr("height", yScale.bandwidth())
      .attr("x",      d => xScale(new Date()))
      .attr("width",  d => xScale(d.end) - xScale(new Date()))
      .attr("fill",   d => colorRemaining(d.party))
      //.attr("rx",     3)
      .on("mouseover", (event, d) => {
        tooltip
        .style("display", "block")
        .style("left", event.pageX + 10 + "px")
        .style("top",  event.pageY - 20 + "px")
        .html(tooltipContentRemaining(d));
        })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.pageX + 12 + "px")
          .style("top",  event.pageY - 28 + "px");
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      });

  // svg.append("line")
  // .attr("x1", xScale(new Date()))
  // .attr("x2", xScale(new Date()))
  // .attr("y1", 0)
  // .attr("y2", innerHeight)
  // .attr("stroke", "#9498a0")
  // .attr("stroke-dasharray", "4,4");
}

