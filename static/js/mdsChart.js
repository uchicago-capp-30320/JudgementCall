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
    const margin = { top: 20, right: 60, bottom: 40, left: 30 }

    const innerWidth  = width  - margin.left - margin.right;
    const innerHeight = height - margin.top  - margin.bottom;


    const partyColor = d3.scaleOrdinal()
        .domain(["republican", "democrat", "independent"])
        .range(["#d62728", "#1f77b4", "#ff7f0e"])
        .unknown("#7f7f7f");

    const coordCount = {};
    const precision = 1;
    const arr = Object.keys(data.x).map(i => {
        const key = `${data.x[i].toFixed(precision)},${data.y[i].toFixed(precision)}`;
        coordCount[key] = (coordCount[key] || 0) + 1;
        return {
            x: data.x[i],
            y: data.y[i],
            x_orig: data.x[i],
            y_orig: data.y[i],
            judge_name: data.judge_name[i],
            ticket_party: data.ticket_party[i],
            appointer_party: data.appointer_party[i],
            selection_type: data.selection_type[i],
            party: data.selection_type[i] == "partisan election" ? data.ticket_party[i] : data.appointer_party[i],
            judge: data.judge[i],
            case: data.case[i],
            _coordKey: key,
            _dupIndex: coordCount[key],
        };
    });

    const jitter = 0.05;
    arr.forEach(d => {
        if (coordCount[d._coordKey] > 1) {
            d._isDuplicate = true;  // ← mark it
            const angle = (2 * Math.PI / coordCount[d._coordKey]) * (d._dupIndex - 1) + Math.PI / 2;
            d.x += jitter * 0.3 * Math.cos(angle);
            d.y += jitter * Math.sin(angle);
        }
    });


    const colorAccessor = d => partyColor(d.appointer_party)

    const dotRadius = 6
    const dotOpacity = 0.75
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
        if (d._isDuplicate) {
            svg.selectAll("text.judge-label")
                .filter(t => t === d)
                .style("display", "block");
        }
        tooltip
            .style("display", "block")
            .style("left", event.pageX + 10 + "px")
            .style("top", event.pageY - 20 + "px")
            .html(tooltipFormat(d));
    })
    .on("mousemove", (event) => {
        tooltip
            .style("left", event.pageX + 12 + "px")
            .style("top",  event.pageY - 28 + "px");
    })
    .on("mouseout", (event, d) => {
        if (d._isDuplicate) {
            svg.selectAll("text.judge-label")
                .filter(t => t === d)
                .style("display", "none");
        }
        tooltip.style("display", "none");
    });

    svg.append('g')
        .selectAll("text")
        .data(arr)
        .enter()
        .append("text")
        .attr("class", d => d._isDuplicate ? "judge-label judge-label-hidden" : "judge-label")
        .attr("x", d => xScale(d.x) + dotRadius + 2)
        .attr("y", d => yScale(d.y) + 4)
        .text(d => d.judge_name)
        .attr("font-size", "11px")
        .attr("fill", "#333")
        .style("pointer-events", "none")
        .style("display", d => d._isDuplicate ? "none" : "block");

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

    // const brush = d3.brush()
    //     .extent([[0, 0], [innerWidth, innerHeight]])
    //     .on("end", ({ selection }) => {
    //         if (!selection) {
    //             clearLines();
    //             return;
    //         }
    //         const [[x0, y0], [x1, y1]] = selection;
    //         const selected = arr.filter(d =>
    //             xScale(d.x) >= x0 && xScale(d.x) <= x1 &&
    //             yScale(d.y) >= y0 && yScale(d.y) <= y1
    //         );
    //         drawDistanceLines(selected);
    //     });

    // svg.append("g").attr("class", "brush").call(brush);

    // const lineGroup = svg.append("g").attr("class", "distance-lines");

    // // Build a color scale based on the range of pairwise distances in the selection
    // function drawDistanceLines(selected) {
    //     clearLines();
    //     if (selected.length < 2) return;

    //     const pairs = [];
    //     for (let i = 0; i < selected.length; i++)
    //         for (let j = i + 1; j < selected.length; j++) {
    //             const a = selected[i], b = selected[j];
    //             const dist = Math.sqrt((a.x_orig - b.x_orig) ** 2 + (a.y_orig - b.y_orig) ** 2);
    //             pairs.push({ a, b, dist });
    //         }

    //     const distExtent = d3.extent(pairs, p => p.dist);
    //     const lineColor = d3.scaleSequential(d3.interpolatePurples)
    //         .domain([distExtent[1], distExtent[0]]);  // ← reversed: short=green, long=red

    //     pairs.forEach(({ a, b, dist }) => {
    //         const x1 = xScale(a.x), y1 = yScale(a.y);
    //         const x2 = xScale(b.x), y2 = yScale(b.y);
    //         const lineLen = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

    //         const line = lineGroup.append("line")
    //             .attr("x1", x1).attr("y1", y1)
    //             .attr("x2", x1).attr("y2", y1)
    //             .attr("stroke", lineColor(dist))  // ← color by distance
    //             .attr("stroke-width", 1.5)
    //             .attr("stroke-dasharray", lineLen)
    //             .attr("stroke-dashoffset", lineLen);

    //         line.transition().duration(600).ease(d3.easeCubicOut)
    //             .attr("x2", x2).attr("y2", y2)
    //             .attr("stroke-dashoffset", 0);
    //     });
    // }

    // function clearLines() {
    //     lineGroup.selectAll("*").remove();
    //}

}

