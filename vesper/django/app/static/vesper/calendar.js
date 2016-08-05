"use strict"


const pageSize = 30;

let circles = null;
let highlightedCircle = null;


function onLoad() {
	
	let stationSelect = document.getElementById("station");
	stationSelect.onchange = onStationChange;
	
	populateMicrophoneOutputSelect();
	setCalendarTitle();
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
	
	// TODO: Query for station microphone outputs with an XHR rather
	// having the server prepare stationMicrophones for us? It seems
	// like the former might scale better to lots of stations.
	
	const stationSelect = document.getElementById("station");
	const microphoneOutputSelect = document.getElementById("microphone");
	
	for (name of stationMicrophoneOutputs[stationSelect.value]) {
		const option = document.createElement("option");
	    option.text = getMicrophoneOutputDisplayName(name)
	    option.value = name;
		microphoneOutputSelect.add(option);
	}

}


function getMicrophoneOutputDisplayName(output_name) {
	
	// When a microphone output name ends with " Output" we display it
	// without that suffix.
	
	const suffix = ' Output'
	if (output_name.endsWith(suffix))
		return output_name.substring(0, output_name.length - suffix.length);
	else
		return output_name
		
}


function setCalendarTitle() {
	
	const micOutputName = getMicrophoneOutputDisplayName(microphoneOutputName);
	
	const title = `${stationName} / ${micOutputName} / ` +
	              `${detectorName} / ${classification} Clips`;
	
	let titleElement = document.getElementById("calendar-title");
	titleElement.innerHTML = title;
	
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
		
	}

}


function addCalendarPeriod(period, periods_) {
	
	let period_ = document.createElement("div");
	period_.className = "period";
	
	// Add period name.
	let name_ = document.createElement("h2");
	name_.className = "period-name";
	name_.innerHTML = period.name;
	period_.appendChild(name_);
	
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
		
		// Add count circle.
		let circle_ = document.createElement("div");
		circle_.className = "circle";
		let radius = getCircleRadius(day.count).toFixed(1);
		let diameter = 2 * radius;
		circle_.setAttribute("data-radius", radius);
		let size = `${diameter}px`;
		circle_.style.width = size;
		circle_.style.height = size;
		day_.appendChild(circle_);
		
		// Add day number.
		let num_ = document.createElement("a");
		num_.className = "day-num";
		let d = day.date;
		let date = formatDate(d);
		num_.href = `/vesper/night?station=${stationName}&` +
				    `microphone_output=${microphoneOutputName}&` +
				    `detector=${detectorName}&` +
				    `classification=${classification}&` +
				    `date=${date}&` +
				    `start=1&size=${pageSize}`;
		num_.innerHTML = d.getDate();
		day_.appendChild(num_);
		
	}
	
	days_.appendChild(day_);
	
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
	        let count = dayCounts[dayNum.toString()] || 0;
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
		return 0;
	else
		return (25 + 15 * Math.log10(count)) / 2;
}


function onMouseMove(event) {

	let x = event.pageX;
	let y = event.pageY;
	
	let circle = getCircleUnderneath(x, y);
	
	if (circle != highlightedCircle) {
		// highlighted circle will change
		
		// Unhighlight old highlighted circle, if any.
		if (highlightedCircle != null) {
		    highlightedCircle.style.backgroundColor = "orange";
		    highlightedCircle.style.zIndex = "0";
		}
		
		highlightedCircle = circle;
		
		// Highlight new highlighted circle, if any.
		if (highlightedCircle != null) {
		    highlightedCircle.style.backgroundColor = "red";
		    highlightedCircle.style.zIndex = "1";
		}
		
	}
	
}


function getCircleUnderneath(x, y) {
	
	let circleUnderneath = null;
	let radiusUnderneath = null;
	
	for (let circle of circles) {
		
		let rect = circle.getBoundingClientRect();
		let left = rect.left + window.scrollX;
		let top = rect.top + window.scrollY;
		
		let radius = parseInt(circle.getAttribute("data-radius"));
		
		let centerX = left + radius;
		let centerY = top + radius;
		
		let distance = getDistance(x, y, centerX, centerY);
		
		if (distance <= radius &&
		        (radiusUnderneath == null || distance < radiusUnderneath)) {
			    // circle is underneath mouse, and its center is closer
			    // to the mouse than any other such circle yet encountered
			
			circleUnderneath = circle;
			radiusUnderneath = radius;
			
		}
		
	}
	
	return circleUnderneath;

}


function getDistance(xa, ya, xb, yb) {
	let dx = xa - xb;
	let dy = ya - yb;
	return Math.sqrt(dx * dx + dy * dy);
}


window.onload = onLoad;
