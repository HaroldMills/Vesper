import { NULL_CHOICE } from '/static/vesper/ui-constants.js';
import { ViewUtils } from '/static/vesper/view/view-utils.js';


const _NONZERO_COUNT_CIRCLE_COLOR = 'orange';
const _ZERO_COUNT_CIRCLE_COLOR = '#A0A0A0';
const _HIGHLIGHTED_CIRCLE_COLOR = '#00AA00';
const _MIN_RADIUS = 12.5;
const _RADIUS_SCALE_FACTOR = 7.5;

let circles = null;
let highlightedCircle = null;

// Module-level state, set via `init` function.
let state = null;

export function init(state_) {

    // Set module-level state.
    state = state_

	// Install event handlers.
    window.onload = onLoad;

}


function onLoad() {
	setTitle();
    addButtonEventListeners();
	setCalendarPeriods();
}


function setTitle() {

    const classificationText =
        state.classification === NULL_CHOICE
		? '' : ` / ${state.classification}`;
        
    const tagText =
        state.tag === NULL_CHOICE ? '' : ` / ${state.tag}`;
        
	const title =
		`${state.stationMicName} / ${state.detectorName}` +
        `${classificationText}${tagText}`;

	const titleElement = document.getElementById('title');
	titleElement.textContent = `${title} Clips`;

	document.title = `Clip Calendar - ${title}`;

}


function addButtonEventListeners() {
    
    // set clip filter button
    const filterButton = document.getElementById('set-clip-filter-button');
    const filterModal = getSetClipFilterModal();
    filterButton.addEventListener('click', _ => filterModal.show());

    // set clip filter modal OK button
    const okButton =
        document.getElementById('set-clip-filter-modal-ok-button');
    okButton.onclick = ViewUtils.onSetClipFilterModalOkButtonClick;
    
}


function getSetClipFilterModal() {
    const modalDiv = document.getElementById('set-clip-filter-modal');
    return bootstrap.Modal.getOrCreateInstance(modalDiv);
}


function setCalendarPeriods() {

	const periodsDiv = document.getElementById('periods');

	if (state.stationMicName === 'None')
		periodsDiv.innerHTML = 'There are no stations in the archive.';

	else if (state.detectorName === 'None')
		periodsDiv.innerHTML = 'There are no detectors in the archive.';

	else if (state.periods.length === 0)
		periodsDiv.innerHTML = 'There are no such clips in the archive.';

	else {

		// The server provides us with a Javascript array called `periods`,
		// each element of which describes a calendar period. It also provides
		// us with an empty <div> element with ID "periods" where the calendar
		// periods should go. We populate the <div> according to the contents
		// of the `periods` array.

		for (const period of state.periods)
			addCalendarPeriod(period, periodsDiv);

		circles = document.querySelectorAll('.circle');

		// Install mouse motion handler on calendar.
		const calendar = document.getElementById('calendar');
		calendar.addEventListener('mousemove', onMouseMove);
		calendar.addEventListener('click', onMouseClick);

	}

}


function addCalendarPeriod(period, periodsDiv) {

	const periodDiv = document.createElement('div');
	periodDiv.className = 'period';

	// Add period name.
//	const nameHeading = document.createElement('h2');
//	nameHeading.className = 'period-name';
//	nameHeading.textContent = period.name;
//	periodDiv.appendChild(nameHeading);

	// Add horizontal rule.
	const rule = document.createElement('hr');
	rule.className = 'period-rule';
	periodDiv.appendChild(rule);

	// Add period rows.
	const rows = getPeriodRows(period);
	for (const row of rows)
		addPeriodRow(row, periodDiv);

	periodsDiv.appendChild(periodDiv);

}


function addPeriodRow(row, periodDiv) {

	const rowDiv = document.createElement('div');
	rowDiv.classList.add('row', 'my-5');

	for (const month of row)
		addRowMonth(month, rowDiv);

	periodDiv.appendChild(rowDiv);

}


function addRowMonth(month, rowDiv) {

	const monthDiv = document.createElement('div');
	monthDiv.classList.add('col-sm-4', 'month');

	if (month !== null) {

		// Add month name.
		if (month.name !== null) {
		    const nameHeading = document.createElement('h4');
		    nameHeading.className = 'month-name';
		    nameHeading.textContent = month.name;
		    monthDiv.appendChild(nameHeading)
		}

		// Add month days.
		const daysDiv = document.createElement('div');
		daysDiv.className = 'month-days';
		for (const day of month.days)
			addMonthDay(day, daysDiv)
		monthDiv.appendChild(daysDiv);

	}

	rowDiv.appendChild(monthDiv);

}


function addMonthDay(day, daysDiv) {

	const dayDiv = document.createElement('div');
	dayDiv.className = 'day';

	if (day === null) {

		// Add empty div for layout.
		const empty = document.createElement('div');
		dayDiv.appendChild(empty);

	} else {

	    
        // Get circle URL.
        const url = new URL(window.location.href);
        url.pathname = '/night';
        const params = url.searchParams;
        params.set('station_mic', state.stationMicName);
        params.set('detector', state.detectorName);
        params.set('classification', state.classification);
        params.set('tag', state.tag);
        params.set('date', formatDate(day.date));
        params.set('settings', state.settingsPresetPath);
        params.set('commands', state.keyBindingsPresetPath);
        
        
		// Add day number.

		let num = null;

		if (day.count === undefined) {
			// no recordings for this day

			num = document.createElement('span');

		} else {
			// one or more recordings for this day

		    num = document.createElement('a');
	        num.href = url.href;
            
            // Add tooltip showing number of clips.
            const tooltipText =
                day.count === 1 ? '1 clip' : `${day.count} clips`;
            num.setAttribute('data-bs-toggle', 'tooltip');
            num.setAttribute('title', tooltipText);

		}

		num.textContent = day.date.getDate();
		num.className = 'day-num';
		dayDiv.appendChild(num);


		// Add count circle.
		
		if (day.count !== undefined) {
			// one or more recordings for this day

			const circleDiv = document.createElement('div');
			circleDiv.className = 'circle';

			// Set circle attributes.
			circleDiv.setAttribute('data-url', url.href);
			circleDiv.setAttribute('data-count', day.count.toString());
			const radius = getCircleRadius(day.count).toFixed(1);
			circleDiv.setAttribute('data-radius', radius);

			// Set circle size.
			const diameter = 2 * radius;
			const size = `${diameter}px`;
			circleDiv.style.width = size;
			circleDiv.style.height = size;

			// Set circle color.
			circleDiv.style.background = getCircleColor(circleDiv);
			circleDiv.style.opacity = .7;

			dayDiv.appendChild(circleDiv);

		}
		

	}

	daysDiv.appendChild(dayDiv);

}


function getCircleColor(circle) {
	const count = Number.parseInt(circle.getAttribute('data-count'));
	return count === 0 ? _ZERO_COUNT_CIRCLE_COLOR : _NONZERO_COUNT_CIRCLE_COLOR;
}


function formatDate(d) {

	// Get four-digit year.
	const yyyy = d.getFullYear().toString();

	// Get two-digit month.
	let mm = (d.getMonth() + 1).toString();
	if (mm.length === 1)
		mm = '0' + mm;

	// Get two-digit day.
	let dd = d.getDate().toString();
	if (dd.length === 1)
		dd = '0' + dd;

	return yyyy + '-' + mm + '-' + dd;

}


function getPeriodRows(period) {

	let months = period.months;
	const numMonths = months.length;

	let initialMonths;
	let finalMonths;

	if (numMonths > 3) {

		const numInitialEmptyMonths = (months[0].month - 1) % 3;
		initialMonths = Array(numInitialEmptyMonths).fill(null);

		const m = (numInitialEmptyMonths + numMonths) % 3;
		const numFinalEmptyMonths = m === 0 ? 0 : 3 - m;
		finalMonths = Array(numFinalEmptyMonths).fill(null);

	} else {
		// three or fewer months

		initialMonths = [];
		finalMonths = Array(3 - numMonths).fill(null);

	}

	months = [].concat(initialMonths, months, finalMonths);

	const rows = [];
	for (let i = 0; i < months.length; i += 3) {
		const rowMonths = months.slice(i, i + 3);
		const monthInfos = rowMonths.map(getMonthInfo);
		rows.push(monthInfos);
	}

//    if (numMonths === 1) {
//        // only one month in this period
//
//        // Suppress display of month name since it's same as period name.
//        rows[0][0].name = null;
//
//    }

	return rows;

}


function getMonthInfo(month) {

	if (month === null) {

		return null;

	} else {

	    const name = getMonthName(month.month) + ' ' + month.year;
	    const numInitialEmptyDays = getWeekdayNumOfFirstMonthDay(month);
	    const length = getMonthLength(month);

	    // Create `dayCounts` object that maps day numbers (as strings)
	    // to counts.
	    const dayCounts = {}
	    for (const dayCount of month.dayCounts) {
	    	dayCounts[dayCount[0].toString()] = dayCount[1];
	    }

	    const days = Array(numInitialEmptyDays + length).fill(null);

	    for (let dayNum = 1; dayNum <= length; dayNum++) {
	    	const date = new Date(month.year, month.month - 1, dayNum);
	        const count = dayCounts[dayNum.toString()]
	        days[numInitialEmptyDays + dayNum - 1] =
	            { 'date': date, 'count': count }
	    }

	    return { 'name': name, 'days': days }

	}

}


const monthNames = [
    null, 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];


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
	if (count === 0)
		return _MIN_RADIUS;
	else
		return _MIN_RADIUS + _RADIUS_SCALE_FACTOR * Math.log10(count);
}


function onMouseMove(event) {

	const x = event.pageX;
	const y = event.pageY;

	const circle = getCircleUnderneath(x, y);

	if (circle !== highlightedCircle) {
		// highlighted circle will change

		// Unhighlight old highlighted circle, if any.
		if (highlightedCircle !== null) {
		    highlightedCircle.style.backgroundColor =
		    	getCircleColor(highlightedCircle);
		    highlightedCircle.style.zIndex = '0';
		}

		highlightedCircle = circle;

		// Highlight new highlighted circle, if any.
		if (highlightedCircle !== null) {
		    highlightedCircle.style.backgroundColor = _HIGHLIGHTED_CIRCLE_COLOR;
		    highlightedCircle.style.zIndex = '1';
		}

	}

}


function getCircleUnderneath(x, y) {

	let circleUnderneath = null;
	let distanceUnderneath = null;

	for (const circle of circles) {

		const rect = circle.getBoundingClientRect();
		const left = rect.left + window.scrollX;
		const top = rect.top + window.scrollY;

		const radius = parseInt(circle.getAttribute('data-radius'));

		const centerX = left + radius;
		const centerY = top + radius;

		const distance = getDistance(x, y, centerX, centerY);

		if (distance <= radius &&
		        (distanceUnderneath === null || distance < distanceUnderneath)) {
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
	const dx = xa - xb;
	const dy = ya - yb;
	return Math.sqrt(dx * dx + dy * dy);
}


function onMouseClick(event) {

	const x = event.pageX;
	const y = event.pageY;

	const circle = getCircleUnderneath(x, y);

	if (circle !== null) {

		const url = circle.getAttribute('data-url');

		if (url !== '')
		    window.location.href = url;

	}

}
