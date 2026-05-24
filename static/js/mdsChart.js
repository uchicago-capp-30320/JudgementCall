const tooltip = d3.select(".mdsContainer")
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


function makeMDSChart(data, selector) {
    const containerWidth = d3.select(selector).node().getBoundingClientRect().width;
    const width  = Math.min(500, containerWidth);
    const height = width * (2/3);
    const margin = { top: 20, right: 30, bottom: 40, left: 30 }

    const innerWidth  = width  - margin.left - margin.right;
    const innerHeight = height - margin.top  - margin.bottom;


    const partyColor = d3.scaleOrdinal()
        .domain(["republican", "democrat", "independent"])
        .range(["#d62728", "#1f77b4", "#ff7f0e"])
        .unknown("#7f7f7f");

    const arr = Object.keys(data.x).map(i => ({
        x: data.x[i],
        y: data.y[i],
        judge_name: data.judge_name[i],
        ticket_party: data.ticket_party[i],
        appointer_party: data.appointer_party[i],
        selection_type: data.selection_type[i],
        party: data.selection_type[i] == "partisan election" ? data.ticket_party[i] : data.appointer_party[i],
        judge: data.judge[i],
        case: data.case[i],
    }));


    const colorAccessor = d => partyColor(d.appointer_party)

    const dotRadius = 6
    const dotOpacity = 1
    const xLabel = "X"
    const yLabel = "Y"
    const tooltipFormat = d => `
        <strong>${d.judge_name}</strong><br>
        Party: ${d.party}<br>
        Selection type: ${d.selection_type}<br>
        Ticket party: ${d.ticket_party}<br>
        Appointed by: ${d.appointer_party}<br>
        Cases: ${d.case}
    `;

    // --- SVG setup ---
    const svg = d3.select(selector)
    .append("svg")
    .attr("width",  width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

    console.log(arr)
    const xExtent = d3.extent(arr, d => d.x);
    const yExtent = d3.extent(arr, d => d.y);
    const xPad = (xExtent[1] - xExtent[0]) * 0.1;
    const yPad = (yExtent[1] - yExtent[0]) * 0.1;

    const xScale = d3.scaleLinear()
    .domain([xExtent[0] - xPad, xExtent[1] + xPad])
    .range([0, innerWidth]);

    const yScale = d3.scaleLinear()
    .domain([yExtent[0] - yPad, yExtent[1] + yPad])
    .range([innerHeight, 0]);

    // Add dots
    svg.append('g')
    .selectAll("dot")
    .data(arr)
    .enter()
    .append("circle")
        .attr("cx", function (d) { return xScale(d.x); } )
        .attr("cy", function (d) { return yScale(d.y); } )
        .attr("r", dotRadius)
        .style("fill", d => partyColor(d.party))
    .on("mouseover", (event, d) => {
        tooltip
            .style("display", "block")
            .style("left", event.pageX + 10 + "px")
            .style("top",  event.pageY - 20 + "px")
            .html(tooltipFormat(d));
        })
    .on("mousemove", (event) => {
        tooltip
            .style("left", event.pageX + 12 + "px")
            .style("top",  event.pageY - 28 + "px");
    })
    .on("mouseout", () => {
        tooltip.style("display", "none");
      });

     // Grid lines
    svg.append("g")
        .call(d3.axisLeft(yScale).tickSize(-innerWidth).tickFormat(""))
        .call(a => a.select(".domain").remove())
        .call(a => a.selectAll("line").attr("stroke", "rgba(0,0,0,0.07)"));

    svg.append("g")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(xScale).tickSize(-innerHeight).tickFormat(""))
        .call(a => a.select(".domain").remove())
        .call(a => a.selectAll("line").attr("stroke", "rgba(0,0,0,0.07)"));

    // Axes
    svg.append("g")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(xScale).ticks(6).tickFormat(""));

    svg.append("g")
        .call(d3.axisLeft(yScale).ticks(6).tickFormat(""));

    // // Axis labels
    // svg.append("text")
    //     .attr("x", margin.left + innerWidth / 2).attr("y", height - 8)
    //     .attr("text-anchor", "middle").attr("font-size", 13)
    //     .text(xLabel);

    // svg.append("text")
    //     .attr("transform", "rotate(-90)")
    //     .attr("x", -(margin.top + innerHeight / 2)).attr("y", 14)
    //     .attr("text-anchor", "middle").attr("font-size", 13)
    //     .text(yLabel);

    // // Tooltip
    // const tooltip = document.getElementById("tooltip");

    // // Dots
    // svg.selectAll("circle")
    //     .data(arr)
    //     .join("circle")
    //     .attr("cx", d => xScale(d.x))
    //     .attr("cy", d => yScale(d.y))
    //     .attr("r", dotRadius)
    //     .attr("fill",d => partyColor(d.ticket_party ? d.ticket_party : d.appointer_party))
    //     .attr("opacity", dotOpacity)
    //     .style("cursor", "pointer")
    //     .on("mouseenter", function(event, d) {
    //     d3.select(this).transition().duration(100)
    //         .attr("r", dotRadius * 1.5).attr("opacity", 1);
    //     tooltip.innerHTML = tooltipFormat(d);
    //     tooltip.style.opacity = "1";
    //     })
    //     .on("mousemove", function(event) {
    //     const rect = container.parentElement.getBoundingClientRect();
    //     const x = event.clientX - rect.left + 12;
    //     const y = event.clientY - rect.top - 10;
    //     tooltip.style.left = Math.min(x, rect.width - tooltip.offsetWidth - 4) + "px";
    //     tooltip.style.top = (y - tooltip.offsetHeight) + "px";
    //     })
    //     .on("mouseleave", function() {
    //     d3.select(this).transition().duration(100)
    //         .attr("r", dotRadius).attr("opacity", dotOpacity);
    //     tooltip.style.opacity = "0";
    //     });

}

