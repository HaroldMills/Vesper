"use strict"


const _NONZERO_COUNT_CIRCLE_COLOR = "orange";
const _ZERO_COUNT_CIRCLE_COLOR = "#A0A0A0";
const _HIGHLIGHTED_CIRCLE_COLOR = "#00AA00";
const _MIN_RADIUS = 12.5;
const _RADIUS_SCALE_FACTOR = 7.5;

let circles = null;
let highlightedCircle = null;


function onLoad() {
	
	let stationSelect = document.getElementById("station");
	stationSelect.onchange = onStationChange;
	
	populateMicrophoneOutputSelect();
	setTitle();
	setCalendarPeriods();
	
}


function onStationChange() {
	clearMicrophoneOutputSelect();
	populateMicrophoneOutputSelect();
}


function clearMicrophoneOutputSelect() {
	
	let microphoneOutputSelect = document.getElementById("microphone");
	
	// Remove old station microphone outputs.
	while (microphoneOutputSelect.length != 0)
		microphoneOutputSelect.remove(0);
	
}


function populateMicrophoneOutputSelect() {
	
	// TODO: Rather than having the server send station microphone
	// outputs to the client, perhaps the client should retrieve the
	// outputs from the server with an XHR. We could set up URLs so
	// that a client could request the microphone outputs for a
	// particular station as JSON.
	
	const stationSelect = document.getElementById("station");
	const microphoneOutputSelect = document.getElementById("microphone");
	
	for (name of stationMicrophoneOutputs[stationSelect.value]) {
		const option = document.createElement("option");
	    option.text = getMicrophoneOutputDisplayName(name)
	    option.value = name;
		microphoneOutputSelect.add(option);
	}

}


function setTitle() {
	
	const micOutputName = getMicrophoneOutputDisplayName(microphoneOutputName);
	
	const title = `${stationName} / ${micOutputName} / ` +
	              `${detectorName} / ${classification} Clips`;
	
	let titleElement = document.getElementById("title");
	titleElement.innerHTML = title;
	
	document.title = `Calendar - ${title}`;
	
}


function setCalendarPeriods() {
	
	let periodsDiv = document.getElementById("periods");
	
	if (stationName === "None")
		periodsDiv.innerHTML = "There are no stations in the archive.";
			
	else if (microphoneOutputName === "None")
		periodsDiv.innerHTML =
			"There are no microphones associated with station " +
			`"${stationName}".`;
	
	else if (detectorName === "None")
		periodsDiv.innerHTML = "There are no detectors in the archive.";
	
	else if (periods.length == 0)
		periodsDiv.innerHTML = "There are no such clips in the archive.";
	
	else {
		
		// The server provides us with a Javascript array called `periods`,
		// each element of which describes a calendar period. It also provides
		// us with an empty <div> element with ID "periods" where the calendar
		// periods should go. We populate the <div> according to the contents
		// of the `periods` array.
		
		for (let period of periods)
			addCalendarPeriod(period, periodsDiv);
			
		circles = document.querySelectorAll(".circle");
		
		// Install mouse motion handler on calendar.
		const calendar = document.getElementById("calendar");
		calendar.addEventListener("mousemove", onMouseMove);
		calendar.addEventListener("click", onMouseClick);
		
	}

}


function addCalendarPeriod(period, periods_) {
	
	let period_ = document.createElement("div");
	period_.className = "period";
	
	// Add period name.
//	let name_ = document.createElement("h2");
//	name_.className = "period-name";
//	name_.innerHTML = period.name;
//	period_.appendChild(name_);
	
	// Add horizontal rule.
	let hr_ = document.createElement("hr");
	hr_.className = "period-rule";
	period_.appendChild(hr_);
	
	// Add period rows.
	let rows = getPeriodRows(period);
	for (let row of rows)
		addPeriodRow(row, period_);
	
	periods_.appendChild(period_);
	
}


function addPeriodRow(row, period_) {
	
	let row_ = document.createElement("div");
	row_.className = "row";
	
	for (let month of row)
		addRowMonth(month, row_);
	
	period_.appendChild(row_);
	
}


function addRowMonth(month, row_) {
	
	let month_ = document.createElement("div");
	month_.className = "col-sm-4 month";
	
	if (month != null) {
		
		// Add month name.
		if (month.name != null) {
		    let name_ = document.createElement("h3");
		    name_.className = "month-name";
		    name_.innerHTML = month.name;
		    month_.appendChild(name_)
		}
		
		// Add month days.
		let days_ = document.createElement("div");
		days_.className = "month-days";
		for (let day of month.days)
			addMonthDay(day, days_)
		month_.appendChild(days_);
	
	}
	
	row_.appendChild(month_);
	
}


function addMonthDay(day, days_) {
	
	let day_ = document.createElement("div");
	day_.className = "day";
	
	if (day == null) {
		
		// Add empty div for layout.
		let empty = document.createElement("div");
		day_.appendChild(empty);
		
	} else {
		
		// Get circle URL.
		let date = formatDate(day.date);
		let url = `/vesper/night?station=${stationName}&` +
				  `microphone_output=${microphoneOutputName}&` +
				  `detector=${detectorName}&` +
				  `classification=${classification}&` +
				  `date=${date}`;
		
		
		// Add day number.
		
		let num_ = null;
		
		if (day.count === undefined) {
			// no recordings for this day
			
			num_ = document.createElement("span");
			
		} else {
			// one or more recordings for this day
			
		    num_ = document.createElement("a");
	        num_.href = url;
		    
		}
		
		num_.innerHTML = day.date.getDate();
		num_.className = "day-num";
		day_.appendChild(num_);
		
		
		// Add count circle.
		if (day.count !== undefined) {
			// one or more recordings for this day
			
			let circle_ = document.createElement("div");
			circle_.className = "circle";
			circle_.setAttribute("data-url", url);
			circle_.setAttribute("data-count", day.count.toString());
			let radius = getCircleRadius(day.count).toFixed(1);
			circle_.setAttribute("data-radius", radius);
			let diameter = 2 * radius;
			let size = `${diameter}px`;
			circle_.style.width = size;
			circle_.style.height = size;
			circle_.style.background = getCircleColor(circle_);
			circle_.style.opacity = .7;
			day_.appendChild(circle_);
			
		}
		
	}
	
	days_.appendChild(day_);
	
}


function getCircleColor(circle) {
	const count = Number.parseInt(circle.getAttribute("data-count"));
	return count === 0 ? _ZERO_COUNT_CIRCLE_COLOR : _NONZERO_COUNT_CIRCLE_COLOR;
}


function formatDate(d) {
	
	// Get four-digit year.
	let yyyy = d.getFullYear().toString();
	
	// Get two-digit month.
	let mm = (d.getMonth() + 1).toString();
	if (mm.length == 1)
		mm = "0" + mm;
	
	// Get two-digit day.
	let dd = d.getDate().toString();
	if (dd.length == 1)
		dd = "0" + dd;
	
	return yyyy + '-' + mm + '-' + dd;

}


function getPeriodRows(period) {
	
	let months = period.months;
	let numMonths = months.length;
	
	let initialMonths;
	let finalMonths;
	
	if (numMonths > 3) {
		
		let numInitialEmptyMonths = (months[0].month - 1) % 3;
		initialMonths = Array(numInitialEmptyMonths).fill(null);
		
		let m = (numInitialEmptyMonths + numMonths) % 3;
		let numFinalEmptyMonths = m == 0 ? 0 : 3 - m;
		finalMonths = Array(numFinalEmptyMonths).fill(null);
		
	} else {
		// three or fewer months
		
		initialMonths = [];
		finalMonths = Array(3 - numMonths).fill(null);
		
	}
	
	months = [].concat(initialMonths, months, finalMonths);

	let rows = [];
	for (let i = 0; i != months.length; i += 3) {
		let rowMonths = months.slice(i, i + 3);
		let monthInfos = rowMonths.map(getMonthInfo);
		rows.push(monthInfos);
	}
	
    if (numMonths == 1) {
        // only one month in this period
        
        // Suppress display of month name since it's same as period name.
        rows[0][0].name = null;
        
    }
        
	return rows;
	
}


function getMonthInfo(month) {
	
	if (month == null) {
		
		return null;
		
	} else {
		
	    let name = getMonthName(month.month) + " " + month.year;
	    let numInitialEmptyDays = getWeekdayNumOfFirstMonthDay(month);
	    let length = getMonthLength(month);
	    
	    // Create `dayCounts` object that maps day numbers (as strings)
	    // to counts.
	    let dayCounts = {}
	    for (let dayCount of month.dayCounts) {
	    	dayCounts[dayCount[0].toString()] = dayCount[1];
	    }
	    
	    let days = Array(numInitialEmptyDays + length).fill(null);
	    
	    for (let dayNum = 1; dayNum != length + 1; ++dayNum) {
	    	let date = new Date(month.year, month.month - 1, dayNum);
	        let count = dayCounts[dayNum.toString()]
	        days[numInitialEmptyDays + dayNum - 1] =
	            { "date": date, "count": count }
	    }
	    
	    return { "name": name, "days": days }
	    
	}
	
}


let monthNames = [
    null, "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"];


/* This really isn't satisfactory since it doesn't support localization.
 * Perhaps we could use the recent ECMAScript Internationalization API on
 * browsers that support it, and fall back on the current implementation
 * on browsers that don't (e.g. Safari)?
 * 
 * Relevant links:
 *     https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/
 *         Global_Objects/DateTimeFormat
 *     http://stackoverflow.com/questions/1643320/get-month-name-from-date
 */
function getMonthName(month) {
	return monthNames[month];
}


function getWeekdayNumOfFirstMonthDay(month) {
	return (new Date(month.year, month.month - 1, 1)).getDay();	
}


function getMonthLength(month) {
	return (new Date(month.year, month.month, 0)).getDate();
}


function getCircleRadius(count) {
	if (count == 0)
		return _MIN_RADIUS;
	else
		return _MIN_RADIUS + _RADIUS_SCALE_FACTOR * Math.log10(count);
}


function onMouseMove(event) {

	let x = event.pageX;
	let y = event.pageY;
	
	let circle = getCircleUnderneath(x, y);
	
	if (circle != highlightedCircle) {
		// highlighted circle will change
		
		// Unhighlight old highlighted circle, if any.
		if (highlightedCircle != null) {
		    highlightedCircle.style.backgroundColor =
		    	getCircleColor(highlightedCircle);
		    highlightedCircle.style.zIndex = "0";
		}
		
		highlightedCircle = circle;
		
		// Highlight new highlighted circle, if any.
		if (highlightedCircle != null) {
		    highlightedCircle.style.backgroundColor = _HIGHLIGHTED_CIRCLE_COLOR;
		    highlightedCircle.style.zIndex = "1";
		}
		
	}
	
}


function getCircleUnderneath(x, y) {
	
	let circleUnderneath = null;
	let distanceUnderneath = null;
	
	for (let circle of circles) {
		
		let rect = circle.getBoundingClientRect();
		let left = rect.left + window.scrollX;
		let top = rect.top + window.scrollY;
		
		let radius = parseInt(circle.getAttribute("data-radius"));
		
		let centerX = left + radius;
		let centerY = top + radius;
		
		let distance = getDistance(x, y, centerX, centerY);
		
		if (distance <= radius &&
		        (distanceUnderneath == null || distance < distanceUnderneath)) {
			    // circle is underneath mouse, and its center is closer
			    // to the mouse than the center of any other circle yet
			    // encountered
			
			circleUnderneath = circle;
			distanceUnderneath = distance;
			
		}
		
	}
	
	return circleUnderneath;

}


function getDistance(xa, ya, xb, yb) {
	let dx = xa - xb;
	let dy = ya - yb;
	return Math.sqrt(dx * dx + dy * dy);
}


function onMouseClick(event) {

	let x = event.pageX;
	let y = event.pageY;
	
	let circle = getCircleUnderneath(x, y);
	let url = circle.getAttribute("data-url");
	
	if (url != '')
	    window.location.href = url;
	
}


window.onload = onLoad;
