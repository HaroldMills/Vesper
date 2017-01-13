'use strict'


const _DEFAULT_PLOT_LIMITS = [17.5, 31.5];
const _RUG_HEIGHT = 25;              // client pixels, also appears in CSS
const _CLIP_LINES_MARGIN = 6;        // client pixels
const _TICK_HEIGHT = 3;              // client pixels
const _TICK_FONT_SIZE = 12.5;        // client pixels
const _RES_FACTOR = 2;               // canvas pixels per client pixel
const _PAGE_DISTANCE_THRESHOLD = 5;  // client pixels

const _SOLAR_EVENT_NAMES = [
    'sunset', 'civilDusk', 'nauticalDusk', 'astronomicalDusk',
    'astronomicalDawn', 'nauticalDawn', 'civilDawn', 'sunrise'
];

const _DAY_COLOR = '#FFFFFF';
const _CIVIL_TWILIGHT_COLOR = '#CCCCCC';
const _NAUTICAL_TWILIGHT_COLOR = '#888888';
const _ASTRONOMICAL_TWILIGHT_COLOR = '#555555';
const _NIGHT_COLOR = '#000000';
const _RECORDING_COLOR = 'rgba(255, 165, 0, .3)';
const _CLIP_COLOR = 'orange';
const _MOUSE_PAGE_COLOR = '#00AA00';
const _CURRENT_PAGE_COLOR = 'magenta';

const _UNDERLAY_SPEC = [
    ['sunset', 'sunrise', _CIVIL_TWILIGHT_COLOR],
    ['civilDusk', 'civilDawn', _NAUTICAL_TWILIGHT_COLOR],
    ['nauticalDusk', 'nauticalDawn', _ASTRONOMICAL_TWILIGHT_COLOR],
    ['astronomicalDusk', 'astronomicalDawn', _NIGHT_COLOR]
];



class NightRugPlot {
	
	
	constructor(parent, div, clips, solarEventTimes) {
		
		this._parent = parent;
		this._div = div;
		this._recordings = [];
		this._clips = clips;
		this._solarEventTimeStrings = solarEventTimes;
		// this._solarEventTimeStrings = null;    // for testing
		
		this._rugCanvas = this._createRugCanvas();
		this._axisCanvas = this._createAxisCanvas();
		this._lastClientWidth = null;
		
		this._clipTimes = this._clips.map(_getClipTime);
		this._solarEventTimes =
			_getSolarEventTimes(this._solarEventTimeStrings);
		
		[this._startTime, this._endTime] = this._getPlotLimits();
		this._tickTimes = _getTickTimes(this._startTime, this._endTime);
		
		this._pageNum = null;
		this._mousePageNum = null;
		
		this._updateIfNeeded();
		
	}


	_createRugCanvas() {
		
	    const canvas = document.createElement('canvas');
	    canvas.id = 'rug-plot-rug';
	    canvas.addEventListener('mouseover', e => this._onMouseEvent(e));
	    canvas.addEventListener('mousemove', e => this._onMouseEvent(e));
	    canvas.addEventListener('mouseout', e => this._onMouseOut(e));
	    canvas.addEventListener('click', e => this._onClick(e));
	    this._div.appendChild(canvas);
	    
	    return canvas;
	    
	}
	
	
	_createAxisCanvas() {
		
	    const canvas = document.createElement('canvas');
	    canvas.id = 'rug-plot-axis';
	    this._div.appendChild(canvas);
	    
	    return canvas;
	    
	}
	
	
	_getPlotLimits() {
		
		if (this._solarEventTimes !== null) {
			
			const startTime = this._solarEventTimes['sunset'] - 1;
			const endTime = this._solarEventTimes['sunrise'] + 1;
			return [startTime, endTime];
			
		} else {
			
			return _DEFAULT_PLOT_LIMITS;
			
		}
		
	}
	
	
	_updateIfNeeded() {
		
		const clientWidth = this._rugCanvas.clientWidth;
		
		if (clientWidth != this._lastClientWidth) {
			
			this._resizeCanvases(clientWidth);
		    this._draw();
		    
		    this._lastClientWidth = clientWidth
		    
		}
		
	}
	
	
	_resizeCanvases(clientWidth) {
		
		// We maintain each canvas at twice its client size to
		// improve rendering quality.

		this._canvasWidth = _RES_FACTOR * clientWidth;
		
		this._rugCanvas.width = this._canvasWidth;
		this._rugCanvas.height = _RES_FACTOR * this._rugCanvas.clientHeight;
		
		this._axisCanvas.width = this._canvasWidth;
		this._axisCanvas.height = _RES_FACTOR * this._axisCanvas.clientHeight;
		
	}
	
	
	_draw() {
		this._drawUnderlay();
		// this._drawRecordingRects();
		this._drawClipLines(0, this._clipTimes.length, _CLIP_COLOR);
		this._updatePageLines(this.pageNum);
		this._updatePageLines(this._mousePageNum);
		this._drawAxis();
	}
	
	
	_drawUnderlay() {
		
		const context = this._rugCanvas.getContext('2d');
		const height = _RUG_HEIGHT * _RES_FACTOR;
		
		if (this._solarEventTimes !== null) {
			
			context.fillStyle = _DAY_COLOR;
			context.fillRect(0, 0, this._canvasWidth, height);
			
			for (const [startName, endName, color] of _UNDERLAY_SPEC) {
				
			    const startTime = this._solarEventTimes[startName];
			    const startX = this._timeToRectX(startTime);
			    
			    const endTime = this._solarEventTimes[endName];
			    const endX = this._timeToRectX(endTime);
			    
			    const width = endX - startX;
			    
			    context.fillStyle = color;
				context.fillRect(startX, 0, width, height);
				
			}
			
		}
		
	}
	
	
	_timeToRectX(time) {
		const x = this._timeToX(time);
		return _getNearestEvenInt(x);
	}
	
	
	_drawRecordingRects() {
		
		const context = this._rugCanvas.getContext('2d');

		// TODO: When we have actual recording data, draw rects accordingly.
		// for (recording of this._recordings) { }
			
		const x = 20 * _RES_FACTOR;
		const y = _CLIP_LINES_MARGIN * _RES_FACTOR;
		const width = this._canvasWidth - 40 * _RES_FACTOR;
		const height =
			(_RUG_HEIGHT - 2 * (_CLIP_LINES_MARGIN + 1)) * _RES_FACTOR;
		
		context.fillStyle = _RECORDING_COLOR;
		context.fillRect(x, y, width, height);
			
	}
	
	
	_drawClipLines(startClipNum, endClipNum, color) {
		
		const context = this._rugCanvas.getContext('2d');
		
		context.strokeStyle = color;
		context.lineWidth = _RES_FACTOR;
		context.lineCap = 'butt';
		context.lineStyle = 'solid';
		
		context.beginPath();

		const y0 = _lineY(_CLIP_LINES_MARGIN);
		const y1 = _lineY(this._rugCanvas.clientHeight - _CLIP_LINES_MARGIN);
				
	    // We bin clips according to the columns of plot pixels in
		// which they fall, and then draw vertical lines in those
		// columns for which the resulting clip counts are not zero.
		// (Note that this means that we never draw more lines than
		// the plot width in pixels. This is satisfying efficient
		// when the number of clips exceeds the plot width, though
		// I don't know whether or not that efficiency is of any
		// practical importance.)
		//
		// This rendering technique results in a plot with crisp
		// lines, but which exhibits fairly pronounced shimmering
		// during resizing. The shimmering occurs because the
		// assignment of clips to plot pixels necessarily changes
		// with the number of pixels.
		//
		// Another approach would be to simply draw a line for each
		// clip at the floating point x coordinate computed by the
		// _timeToX method. This results in a plot whose lines'
		// crispness varies across clips, depending on where the clip
		// times happen to fall in relation to pixel boundaries, but
		// which is less prone to shimmering during resizing.
		//
		// I tried both techniques and chose to retain the binning
		// one, figuring that the consistently crisp clip lines are
		// more important than the reduced shimmering. I don't expect
		// the shimmering to be much of an issue since I don't expect
		// that users will resize rug plots very often.
		
		const xs = this._getLineXs(startClipNum, endClipNum);
		
		for (const x of xs) {
			context.moveTo(x, y0);
			context.lineTo(x, y1);
		}
		
		context.stroke();
		
	}
	
	
	/*
	 * Gets x coordinates of clip lines.
	 */
	_getLineXs(startClipNum, endClipNum) {
		
		const xs = new Set();
		
		for (let i = startClipNum; i < endClipNum; i++) {
			const time = this._clipTimes[i];
			const x = this._timeToLineX(time);
			if (x !== null)
			    xs.add(x);
		}
		
		return xs;
		
	}
	
		
	_updatePageLines(pageNum) {
		
		if (pageNum !== null) {
			
			let color = _CLIP_COLOR;
			
			if (pageNum === this._pageNum)
			    color = _CURRENT_PAGE_COLOR;
			
			else if (pageNum === this._mousePageNum)
				color = _MOUSE_PAGE_COLOR;
			
			const [start, end] = this._parent.getPageClipNumRange(pageNum);
			this._drawClipLines(start, end, color);
			
		}
		
	}
	
	
	_drawAxis() {
		
		const context = this._axisCanvas.getContext('2d');
		
		// line properties
		context.strokeStyle = 'black';
		context.lineWidth = _RES_FACTOR;
		context.lineStyle = 'solid';
		
		// text properties
		const fontSize = _TICK_FONT_SIZE * _RES_FACTOR;
		context.font = fontSize.toString() + 'px sans-serif';
		context.textAlign = 'center';
		
		context.beginPath();
		
		const y0 = _lineY(0);
		
		for (const t of this._tickTimes) {
			
			const x = this._timeToLineX(t);
			
			if (x !== null) {
				
				const y = _lineY(_TICK_HEIGHT);
				
				context.moveTo(x, y0);
				context.lineTo(x, y);
				
				const hour = t < 24 ? t : t - 24;
				const text = hour.toString();
				context.fillText(text, x, y + fontSize);
				
			}
			
		}
		
		context.stroke();
		
	}
	
	
	_timeToLineX(time) {
		const x = _getNearestOddInt(this._timeToX(time))
		return (x < 0 || x >= this._canvasWidth) ? null : x;
	}
	
	
	_timeToX(time) {
		const deltaTime = this._endTime - this._startTime;
		return this._canvasWidth * (time - this._startTime) / deltaTime;
		
	}
	
	
	get pageNum() {
		return this._pageNum;
	}
	
	
	set pageNum(pageNum) {
		
		if (pageNum != this._pageNum) {
			
			const oldPageNum = this._pageNum;
			this._pageNum = pageNum;
			
			this._updatePageLines(oldPageNum);
			this._updatePageLines(pageNum);

		}
		
	}
	
	
    _onMouseEvent(e) {
    	const pageNum = this._getMousePageNum(e);
    	this._setMousePageNum(pageNum);
    }
    
    
    _getMousePageNum(e) {
    	
		if (this._clipTimes.length === 0)
			// no clips
			
			return null;
    	
		else {
			// at least one clip
			
	    	const clipTimes = this._clipTimes;
			const numClips = clipTimes.length;
	    	const firstClipX = this._timeToClientX(clipTimes[0]);
	    	const lastClipX = this._timeToClientX(clipTimes[numClips - 1]);
	    	
	    	const rect = this._rugCanvas.getBoundingClientRect();
	    	const mouseX = e.clientX - rect.left;
	    	
	    	if (firstClipX - mouseX > _PAGE_DISTANCE_THRESHOLD ||
	    			mouseX - lastClipX > _PAGE_DISTANCE_THRESHOLD)
	    		// mouse is too far to left or right of clips
	    		
	    		return null;
	    	
	    	else {
	    		// mouse is within clips, or close enough to first or last
	    		
		    	const time = this._clientXToTime(mouseX);
		    	const clipNum = this._findClosestClipNum(time);
		    	return this._parent.getClipPageNum(clipNum);

	    	}
	    	
		}
	    		
    }
    
    
	_timeToClientX(time) {
		const clientWidth = this._rugCanvas.clientWidth
		const deltaTime = this._endTime - this._startTime;
		return clientWidth * (time - this._startTime) / deltaTime;
	}
	
	
	_clientXToTime(x) {
		const deltaTime = this._endTime - this._startTime;
		const width = this._rugCanvas.clientWidth;
		return this._startTime + x * deltaTime / width;
	}
	
	
	_findClosestClipNum(time) {
		
		const clipTimes = this._clipTimes;
		const numClips = clipTimes.length;
		
		if (numClips === 0)
			return null;
		
		else {
			
		    const clipNum = findLastLE(clipTimes, time);
		    
		    if (clipNum === -1)
		    	return 0;
		    
		    else if (clipNum === numClips - 1)
		    	return numClips - 1;
		    
		    else {
		    	const d0 = time - clipTimes[clipNum];
		    	const d1 = clipTimes[clipNum + 1] - time;
		    	return d0 < d1 ? clipNum : clipNum + 1;
		    }
		    	
		}
		
	}
	
	
	_setMousePageNum(pageNum) {
		
		if (pageNum != this._mousePageNum) {
			
			const oldPageNum = this._mousePageNum;
			this._mousePageNum = pageNum;
			
			this._updatePageLines(oldPageNum);
			this._updatePageLines(pageNum);
			
		}
		
	}
	
	
    _onMouseOut(e) {
	    this._setMousePageNum(null);
    }
    
    
    _onClick(e) {
    	this._parent.pageNum = this._getMousePageNum(e);
    }
    
    
	onResize(e) {
		this._updateIfNeeded();
	}
	
	
}


function _getSolarEventTimes(solarEventTimeStrings) {
	
	if (solarEventTimeStrings !== null) {

		const times = {};
		
		for (const eventName of _SOLAR_EVENT_NAMES) {
			const timeObject = _parseTime(solarEventTimeStrings[eventName]);
			times[eventName] = _timeObjectToHours(timeObject);
		}
		
		return times;
		
	} else {
		
		return null;
		
	}
	
}



/*
 * Gets the odd integer nearest x.
 * 
 * Since the sizes of our canvases are twice those of their clients, drawing
 * lines at odd coordinates improves rendering quality.
 */
function _getNearestOddInt(x) {
	const floor = Math.floor(x);
	return (floor % _RES_FACTOR == 1) ? floor : (floor + 1);
}


/*
 * Gets the even integer nearest x.
 * 
 * Since the sizes of our canvases are twice those of their clients, filling
 * rectangles at even coordinates improves rendering quality.
 */
function _getNearestEvenInt(x) {
	const floor = Math.floor(x);
	return (floor % _RES_FACTOR == 0) ? floor : (floor + 1);
}


function _getClipTime(clip) {
	const time = _parseTime(clip.localStartTime);
	return _timeObjectToHours(time);
}


/*
 * Converts a time object to a number of hours past midnight of the day
 * on which the night of the clip starts. The description of these units
 * is somewhat complicated, but they are handy for plotting!
 */
function _timeObjectToHours(t) {
	const hourOffset = t.hour >= 12 ? 0 : 24;
	const hour = t.hour + hourOffset;
	const seconds =
        hour * 3600 + t.minute * 60 + t.second + t.millisecond / 1000.;
	return seconds / 3600;
}


/*
 * Parses a string time into an object with 'year', 'month', 'day',
 * etc. properties.
 */
function _parseTime(s) {
	
	// Get start time parts as strings.
	const [date, time, timeZone] = s.split(' ');
	const [year, month, day] = date.split('-');
	const [hour, minute, sec] = time.split(':');
	const [second, millisecond] =
		sec.includes('.') ? sec.split('.') : [sec, '0']

	const toInt = Number.parseInt;
	
	return {
		'year': toInt(year),
		'month': toInt(month),
		'day': toInt(day),
		'hour': toInt(hour),
		'minute': toInt(minute),
		'second': toInt(second),
		'millisecond': toInt(millisecond),
		'timeZone': timeZone
	};
	
}


/*
 * Gets the even-numbered hours between the specified start and end times.
 */
function _getTickTimes(startTime, endTime) {
	
	const start = startTime / 2;
	const end = endTime / 2;
	
	const times = [];
	for (let x = Math.ceil(start); x <= end; x++)
		times.push(2 * x);
	
	return times;
	
}


/*
 * Gets the y canvas coordinate of a vertical line end.
 */
function _lineY(y) {
	return _RES_FACTOR * y;
}
