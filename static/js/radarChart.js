/////////////////////////////////////////////////////////
/////////////// The Radar Chart Function ////////////////
/////////////// Written by Nadieh Bremer ////////////////
////////////////// VisualCinnamon.com ///////////////////
//////////Updated for d3.js v4 by Ingo Kleiber //////////
/////////// Inspired by the code of alangrafu ///////////
//// Legend and other updates by Team Judgement Call ////
/////////////////////////////////////////////////////////

function RadarChart(id, data, options) {
    // Edit this cfg from the `options` arg passed in radar_test.html!
    var cfg = {
        w: 600,				//Width of the circle
        h: 600,				//Height of the circle
        margin: {top: 20, right: 20, bottom: 20, left: 20}, //The margins of the SVG
        legendRadarBuffer: 15, //Extra space between legend and radar
        levels: 3,				//How many levels or inner circles should there be drawn
        maxValue: 0, 			//What is the value that the biggest circle will represent
        labelFactor: 1.33, 	//How much farther than the radius of the outer circle should the axis labels be placed
        lineSpace: 1.2,     //Line spacing between legend items
        wrapWidth: 100, 		//The number of pixels after which a label needs to be given a new line
        opacityArea: 0.5, 	//The base opacity of the area of the blob
        opacityAreaLow: 0.35, 	//The opacity of the area of the blob when another area is hovered over
        opacityAreaHigh: 0.7, 	//The opacity of the area of the blob when hovered over
        dotRadius: 8, 			//The size of the colored circles of each blog
        opacityCircles: 0.1, 	//The opacity of the circles of each blob
        strokeWidth: 2, 		//The width of the stroke around each blob
        roundStrokes: true,	//If true the area and stroke will follow a round path (cardinal-closed)
        color: d3.schemeCategory10	//Color function
    };

    //Put all of the options into a variable called cfg
    if('undefined' !== typeof options){
        for(var i in options){
            if('undefined' !== typeof options[i]){ cfg[i] = options[i]; }
        }//for i
    }//if

    // // If the supplied maxValue is smaller than the actual one, replace by the max in the data
    var maxValue = Math.max(cfg.maxValue, d3.max(data, function(i){return d3.max(i.map(function(o){return o.value;}))}));
    var allAxis = (data[0].map(function(i, j){return i.axis})),	//Names of each axis
        total = allAxis.length,					//The number of different axes
        radius = Math.min(cfg.w/2, cfg.h/2), 	//Radius of the outermost circle
        Format = d3.format('.0%'),			 	//Percentage formatting
        angleSlice = Math.PI * 2 / total;		//The width in radians of each "slice"

    //Scale for the radius
    var rScale = d3.scaleLinear()
        .range([0, radius])
        .domain([0, maxValue]);
    /////////////////////////////////////////////////////////
    //////////// Create the container SVG and g /////////////
    /////////////////////////////////////////////////////////

    //Remove whatever chart with the same id/class was present before
    d3.select(id).select("svg").remove();

    //Initiate the radar chart SVG
    var svg = d3.select(id).append("svg")
            .attr("width",  cfg.w + cfg.margin.left + cfg.margin.right)
            .attr("height", cfg.h + cfg.margin.top + cfg.margin.bottom)
            .attr("class", "radar"+id);
    //Append a g element
    var g = svg.append("g")
            .attr("transform", "translate(" + (cfg.legendRadarBuffer + cfg.w/2 + cfg.margin.left) + "," + (cfg.h/2 + cfg.margin.top) + ")");

    /////////////////////////////////////////////////////////
    ////////// Glow filter for some extra pizzazz ///////////
    /////////////////////////////////////////////////////////

    //Filter for the outside glow
    var filter = g.append('defs').append('filter').attr('id','glow'),
        feGaussianBlur = filter.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','coloredBlur'),
        feMerge = filter.append('feMerge'),
        feMergeNode_1 = feMerge.append('feMergeNode').attr('in','coloredBlur'),
        feMergeNode_2 = feMerge.append('feMergeNode').attr('in','SourceGraphic');

    /////////////////////////////////////////////////////////
    /////////////// Draw the Circular grid //////////////////
    /////////////////////////////////////////////////////////

    //Wrapper for the grid & axes
    var axisGrid = g.append("g").attr("class", "axisWrapper");

    //Draw the background circles
    axisGrid.selectAll(".levels")
    .data(d3.range(1,(cfg.levels+1)).reverse())
    .enter()
        .append("circle")
        .attr("class", "gridCircle")
        .attr("r", function(d, i){return radius/cfg.levels*d;})
        .style("fill", "#CDCDCD")
        .style("stroke", "#CDCDCD")
        .style("fill-opacity", cfg.opacityCircles)
        .style("filter" , "url(#glow)");

    //NEW: Emphasize 50% threshold
    axisGrid.append("circle")
        .attr("class", "gridCircle")
        .attr("r", radius/2)
        .style("fill", "#00000005")
        .style("stroke", "#000000")
        .style("stroke-width", "3")
        .style("stroke-dasharray", "8 8")
        .style("fill-opacity", 1.0)
        .style("filter" , "url(#glow)");

    //Text indicating at what % each level is
    axisGrid.selectAll(".axisLabel")
    .data(d3.range(1,(cfg.levels+1)).reverse())
    .enter().append("text")
    .attr("class", "axisLabel")
    .attr("x", 4)
    .attr("y", function(d){return -d*radius/cfg.levels;})
    .attr("dy", "-0.2em")
    .style("font-size", "15px")
    .attr("fill", "#111111")
    .text(function(d,i) { return Format(maxValue * d/cfg.levels); });

    /////////////////////////////////////////////////////////
    //////////////////// Draw the axes //////////////////////
    /////////////////////////////////////////////////////////

    //Create the straight lines radiating outward from the center
    var axis = axisGrid.selectAll(".axis")
        .data(allAxis)
        .enter()
        .append("g")
        .attr("class", "axis");
    //Append the lines
    axis.append("line")
        .attr("x1", 0)
        .attr("y1", 0)
        .attr("x2", function(d, i){ return rScale(maxValue*1.1) * Math.cos(angleSlice*i - Math.PI/2); })
        .attr("y2", function(d, i){ return rScale(maxValue*1.1) * Math.sin(angleSlice*i - Math.PI/2); })
        .attr("class", "line")
        .style("stroke", "grey")
        .style("stroke-width", "4px");

    //Append the labels at each axis (issue area)
    axis.append("text")
        .attr("class", "legend")
        .style("font-size", "14px")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("x", function(d, i){ return rScale(maxValue * cfg.labelFactor) * Math.cos(angleSlice*i - Math.PI/2); })
        .attr("y", function(d, i){ return rScale(maxValue * cfg.labelFactor) * Math.sin(angleSlice*i - Math.PI/2); })
        .text(function(d){return d})
        .call(wrap, cfg.wrapWidth);

    /////////////////////////////////////////////////////////
    ///////////// Draw the radar chart blobs ////////////////
    /////////////////////////////////////////////////////////

    //The radial line function
    var radarLine = d3.radialLine()
        .curve(d3.curveLinearClosed) // curveNatural
        .radius(function(d) { return rScale(d.value); })
        .angle(function(d,i) {	return i*angleSlice; });

    if(cfg.roundStrokes) {
        radarLine.curve(d3.curveCardinalClosed); // curveLinearClosed
    }

    //Create a wrapper for the blobs
    var blobWrapper = g.selectAll(".radarWrapper")
        .data(data)
        .enter().append("g")
        .attr("class", "radarWrapper");

    //Append the backgrounds
    blobWrapper
        .append("path")
        .attr("class", function(d,i) {
            return "radarArea" + " " + `group-${i}`
        }) // Group name reference for legend
        .attr("d", function(d,i) { return radarLine(d); })
        .style("fill", function(d,i) { return cfg.color(i); })
        .style("fill-opacity", cfg.opacityArea)
        .on("mouseover", function (d,i){
            handle_mouseover_fades(d,i);
        })
        .on("mouseout", function(d,i){
            handle_mouseout_fades(d,i);
        });

    //Create the outlines
    blobWrapper.append("path")
        .attr("class", "radarStroke")
        .attr("d", function(d,i) { return radarLine(d); })
        .style("stroke-width", cfg.strokeWidth + "px")
        .style("stroke", function(d,i) { return cfg.color(i); })
        .style("fill", "none")
        .style("filter" , "url(#glow)");

    //Append the circles (data points themselves)
    blobWrapper.selectAll(".radarCircle")
        .data(function(d,i) { return d; })
        .enter().append("circle")
        .attr("class", "radarCircle")
        .attr("r", cfg.dotRadius)
        .attr("cx", function(d,i){
            return rScale(d.value) * Math.cos(angleSlice*i - Math.PI/2);
        })
        .attr("cy", function(d,i){ return rScale(d.value) * Math.sin(angleSlice*i - Math.PI/2); })
        .style("fill", function(d, i){ return cfg.color(d.name) }) // HOW TO MAKE THESE MATCH BLOB COLORS
        .style("fill-opacity", 0.5)
        .style("stroke", "#000000");

    /////////////////////////////////////////////////////////
    //////// Append invisible circles for tooltip ///////////
    /////////////////////////////////////////////////////////

    //Wrapper for the invisible circles on top
    var blobCircleWrapper = g.selectAll(".radarCircleWrapper")
        .data(data)
        .enter().append("g")
        .attr("class", "radarCircleWrapper");

    //Append a set of invisible circles on top for the mouseover pop-up
    blobCircleWrapper.selectAll(".radarInvisibleCircle")
        .data(function(d,i) { return d; })
        .enter().append("circle")
        .attr("class", "radarInvisibleCircle")
        .attr("r", cfg.dotRadius*1.5)
        .attr("cx", function(d,i){ return rScale(d.value) * Math.cos(angleSlice*i - Math.PI/2); })
        .attr("cy", function(d,i){ return rScale(d.value) * Math.sin(angleSlice*i - Math.PI/2); })
        .style("fill", "none")
        .style("pointer-events", "all")
        .on("mouseover", function(d,i) {
            newX =  parseFloat(d3.select(this).attr("cx")) - 10;
            newY =  parseFloat(d3.select(this).attr("cy")) - 10;
            console.log(cfg.color.domain());
            console.log(d.target.__data__.name);
            tooltip
                .attr("x", newX)
                .attr("y", newY)
                .text(Format(d.target.__data__.value))
                .style("fill", cfg.color(d.target.__data__.name))
                .transition().duration(200)
                .style("opacity", 1);
        })
        .on("mouseout", function(){
            tooltip.transition().duration(200)
                .style("opacity", 0);
        });

    //Set up the small tooltip for when you hover over a circle
    var tooltip = g.append("text")
        .attr("class", "tooltip")
        .style("pointer-events", "none")
        .style("font-size", "2em")
        // .style("text-shadow", "2px 1px 1px black")
        .style("stroke", "black")
        .style("stroke-width", "2px")
        .style("paint-order", "stroke fill")
        .style("opacity", 0)
        .style("filter" , "url(#glow)");

    /////////////////////////////////////////////////////////
    ///////////////// NEW: Draw the Legend //////////////////
    /////////////////////////////////////////////////////////
    //Append another g element
    var g_legend = svg.append("g")
        .attr("transform", "translate(" + (-cfg.w/2) + "," + (cfg.margin.top) + ")")
        .attr("id", "legendBBox");
    var size = 20;
    var nudge = 15;

    g_legend.selectAll(".radarLegendIcon")
    .data(data)
    .enter()
    .append("rect")
        .attr("x", 200 + nudge)
        .attr("y", function(d,i){ return nudge + cfg.lineSpace*i*(size+5) }) // 100 is where the first dot appears. 25 is the distance between dots
        .attr("width", size)
        .attr("height", size)
        .attr("rx", "5")
        .attr("class", function(d,i) {
            return "radarLegendIcon" + " " + `group-${i}`
        }) // For name reference to legend
        .style("fill", function(d,i) { return cfg.color(i); })
        .style("filter" , "url(#glow)")
        .on("mouseover", function (d,i){
            handle_mouseover_fades(d,i);
        })
        .on("mouseout", function(d,i){
            handle_mouseout_fades(d,i);
        });

    g_legend.selectAll(".radarLegendLabel")
    .data(data)
    .enter()
    .append("text")
        .attr("x", nudge + 200 + size*1.1)
        .attr("y", function(d,i){ return nudge + cfg.lineSpace*i*(size+5)}) //Position exactly to icon y
        .attr("dy", "1em") //...then eek the text down by its own size so it's vertically center-aligned!
        .attr("class", function(d,i) {
            return "radarLegendLabel " + `group-${i}`
        })
        .attr("text-anchor", "left")
        // .style("fill", function(d,i) { return cfg.color(i); })
        .style("fill", "#2c2c2c")
        .style("alignment-baseline", "middle")
        .style("font-size", "0.75em")
        .text(function(d){
            return d[0].name; // Like creating allAxis, just use first element (should all be same name anyway)
        })
        .on("mouseover", function (d,i){
            handle_mouseover_fades(d,i);
        })
        .on("mouseout", function(d,i){
            handle_mouseout_fades(d,i);
        });
        //.call(wrap, cfg.wrapWidth*2); //Would be nice to line-wrap long names in legend
    const legendWidth = d3.select("#legendBBox")
        .node()
        .getBBox().width;
    g_legend.append("rect")
        .attr("x", 200)
        .attr("y", 0)
        .attr("width", legendWidth + 2*nudge)
        .attr("height", cfg.lineSpace*2*(size+5)+5 + nudge)
        .attr("rx", 10)
        .style("fill", "#CDCDCD")
        .style("stroke", "#CDCDCD")
        .style("fill-opacity", cfg.opacityCircles)
        .style("filter" , "url(#glow)")
        .lower(); //Draw below legend content; update rect width to actual text length

    /////////////////////////////////////////////////////////
    /////////////////// Helper Function /////////////////////
    /////////////////////////////////////////////////////////

    //Taken from http://bl.ocks.org/mbostock/7555321
    //Wraps SVG text
    function wrap(text, width) {
        text.each(function() {
            var text = d3.select(this),
                words = text.text().split(/\s+/).reverse(),
                word,
                line = [],
                lineNumber = 0,
                lineHeight = 1.4, // ems
                y = text.attr("y"),
                x = text.attr("x"),
                dy = parseFloat(text.attr("dy")),
                tspan = text.text(null).append("tspan").attr("x", x).attr("y", y).attr("dy", dy + "em");

            while (word = words.pop()) {
            line.push(word);
            tspan.text(line.join(" "));
            if (tspan.node().getComputedTextLength() > width) {
                line.pop();
                tspan.text(line.join(" "));
                line = [word];
                tspan = text.append("tspan").attr("x", x).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
            }
            }
        });
    }//wrap

    //Function to apply to elements grouped by class, then a function nested inside
    //that one to handle the if-thens of different opacities for radarArea, legendLabel, etc.
    //Handles opacity transitinos involved when hovering over chart elements
    function handle_mouseover_fades(d, i) {
        //Dim all blobs
        console.log("HERE");
        console.log(i);
        console.log(d);
        d3.selectAll(".radarArea")
            .transition().duration(200)
            .style("fill-opacity", cfg.opacityAreaLow);
        //Dim all legend name labels
        d3.selectAll(".radarLegendLabel")
            .transition().duration(200)
            .style("fill-opacity", cfg.opacityAreaLow);
        //Dim all legend icons
        d3.selectAll(".radarLegendIcon")
            .transition().duration(200)
            .style("fill-opacity", cfg.opacityAreaLow);

        //.originalTarget vs. .explicitOriginalTarget? Latter selects both labels (bad)
        const this_class = d.originalTarget.attributes.class.nodeValue;
        const regex = /group-[\d]+/;
        const this_group = this_class.match(regex)[0]; //.split(' ').at(-1);
        //Bring back the hovered-over blob
        console.log(this_group);
        d3.select(".radarArea" + "." + this_group)
            .transition().duration(200)
            .style("fill-opacity", cfg.opacityAreaHigh);
        //Bring back the name label associated with the hovered-over blob
        //When CSS selecting by multiple classes, no spaces between class names!
        d3.select(".radarLegendLabel" + "." + this_group)
            .transition().duration(200)
            .style("fill-opacity", 1.0);
        //Bring back the name label associated with the hovered-over blob.
        d3.select(".radarLegendIcon" + "." + this_group)
            .transition().duration(200)
            .style("fill-opacity", 1.0);
    }

    function handle_mouseout_fades(d, i) {
        //Bring every chart element back to full opacity
        d3.selectAll(".radarArea")
            .transition().duration(200)
            .style("fill-opacity", cfg.opacityArea);
        d3.selectAll(".radarLegendLabel")
            .transition().duration(200)
            .style("fill-opacity", 1.0);
        d3.selectAll(".radarLegendIcon")
            .transition().duration(200)
            .style("fill-opacity", 1.0);

    }

}//RadarChart
//The radar chart template was provided without a legend, so it might
//take more rearranging of their starter code to have a nice design
//for adapting to a legend. Ideally, elements that fade in and out
//together should maybe be created (appended) together. That avoids
//copy-paste of `.attr("class", ...)` across blobs, legendLabel, etc.