'use strict'


class Multiselection {
	
	
	constructor(minIndex, maxIndex) {
		this._minIndex = minIndex;
		this._maxIndex = maxIndex;
		this._intervals = [];
		this._anchorIndex = null;
		this._anchorIntervalIndex = null;
	}
	
	
	get minIndex() {
		return this._minIndex;
	}
	
	
	get maxIndex() {
		return this._maxIndex;
	}
	
	
	get anchorIndex() {
		return this._anchorIndex;
	}
	
	
	get selectedIntervals() {
		// Return a copy of the intervals list rather than the list itself.
		return this._intervals.map(i => [i[0], i[1]]);
	}
	
	
	get selectedIndices() {
		const indexLists = this._intervals.map(_getIntervalIndices);
		return [].concat(...indexLists);
	}
	
	
	get size() {
		return this._intervals.reduce(_getSizeAux, 0);
	}
	
	
	contains(index) {
		return (this._findContainingInterval(index) !== null);
	}
	
	
	_findContainingInterval(index) {
		
		for (let i = 0; i < this._intervals.length; i++)
			if (_contains(this._intervals[i], index))
			    return i;
		
		// If we get here, no selected interval contains index `index`.
		return null;
		
	}
	
	
	select(index) {
        this._intervals = [[index, index]];
        this._anchorIndex = index;
        this._anchorIntervalIndex = 0;
	}
	
	
	extend(index) {
		
		const intervals = this._intervals;
		
		if (this._anchorIndex === null) {
			
			this._anchorIndex = this._minIndex;
			intervals.push([this._minIndex, index]);
			
		} else {
			
			const i = this._anchorIntervalIndex;
			
			if (index <= this._anchorIndex)
				intervals[i] = [index, this._anchorIndex];
			else
				intervals[i] = [this._anchorIndex, index];
			
		}
		
		this._normalize();
		
	}
    
	
    /*
     * Normalizes the internal data structures of this selection.
     * 
     * When this method is called:
     * 
     *     * The intervals of `this._intervals` may not be disjoint,
     *       and they may not be ordered by increasing start index.
     *       
     *     * `this._anchorIndex` is what it should be, but
     *       `this._anchorIntervalIndex` is undefined.
     *       
     * Upon return:
     * 
     *     * The intervals of `this._intervals` are disjoint and in
     *       order of increasing start index.
     *       
     *     * `this._anchorIndex` is unchanged, and if it is not `None`,
     *       the interval `this._intervals[this._anchorIntervalIndex]`
     *       contains it.
     */
	_normalize() {
		
		const olds = this._intervals;
		
		if (olds.length > 0) {
			
			olds.sort(_compareIntervals);
			
			const news = this._intervals = [olds[0]];
			
			if (_contains(news[news.length - 1], this._anchorIndex))
				this._anchorIntervalIndex = news.length - 1;
			
			for (let i = 1; i < olds.length; i++) {
				
				const w = olds[i];
				const v = news[news.length - 1];
				
				// Note that in the calls to `_combinable` and `_union`
				// the order of `v` and `w` matters.
				
				if (_combinable(v, w))
					news[news.length - 1] = _union(v, w);
				else
					news.push(w);
				
				if (_contains(news[news.length - 1], this._anchorIndex))
					this._anchorIntervalIndex = news.length - 1;
				
			}
			
		}
		
	}
	
	
	toggle(index) {
		
		const intervals = this._intervals;
		
		const i = this._findContainingInterval(index);
		
		if (i === null) {
			// item to be toggled is not selected
			
			intervals.push([index, index]);
			this._anchorIndex = index;
			this._normalize();
			
		} else {
			// item to be toggled is selected
			
			const [a, b] = intervals[i];
			
			if (a !== b) {
				// part of interval will remain selected after item
				// `index` is deselected
				
		        // Delete interval `i`.
				intervals.splice(i, 1);
				
				if (index === b) {
					
					intervals.push([a, b - 1]);
					this._anchorIndex = index - 1;
					
				} else {
					
					if (index !== a)
						intervals.push([a, index - 1]);
					
					intervals.push([index + 1, b]);
					this._anchorIndex = index + 1;
						
				}
				
				this._normalize();
				
			} else {
				// no part of interval will remain selected after item
				// `index` is deselected
				
				if (i !== intervals.length - 1)
					// interval is not last selected interval
					
					this._anchorIndex = intervals[i + 1][0];
				
				else if (i !== 0)
					// interval is last selected interval but another
					// precedes it
					
					this._anchorIndex = intervals[i - 1][1];
				
				else
					// interval is only selected interval
					
					this._anchorIndex = null;
				
		        // Delete interval `i`.
				intervals.splice(i, 1);
				
			}
			
		}
		
	}
	
    
}


function _getSizeAux(acc, interval) {
	const [a, b] = interval;
	return acc + b - a + 1;
}


function _compareIntervals([a0, b0], [a1, b1]) {
	
	if (a0 < a1)
		return -1;
	else if (a0 > a1)
		return 1;
	else if (b0 < b1)
		return -1;
	else if (b0 > b1)
		return 1;
	else
		return 0;
	
}


function _contains(v, i) {
	return v[0] <= i && i <= v[1];
}


function _combinable(v, w) {
	// Caller ensures that v[0] <= w[0].
	return v[1] >= w[0] - 1;
}


function _union(v, w) {
	// Caller ensures that x[0] <= w[0] and v[1] >= w[0].
	return [v[0], Math.max(v[1], w[1])];
}


function _getIntervalIndices([startIndex, endIndex]) {
	return rangeArray(startIndex, endIndex + 1);
}
