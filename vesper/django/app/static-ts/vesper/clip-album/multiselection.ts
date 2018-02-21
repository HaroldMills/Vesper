/*
 * Selection comprising one or more index intervals.
 */


import { ArrayUtils } from '../util/array-utils.js';


export class Multiselection {


	// The minimum selected index.
    private _minIndex: number;

	// The maximum selected index.
	private _maxIndex: number;

	// The selected index intervals of this selection.
	private _intervals: [number, number][];

	// The index of the selection anchor, or `null` if there is none.
	private _anchorIndex: number | null;

	// The index in `_intervals` of the interval containing the
	// selection anchor, or `null` if there is no selection anchor.
	private _anchorIntervalIndex: number | null;


	constructor(minIndex: number, maxIndex: number) {
		this._minIndex = minIndex;
		this._maxIndex = maxIndex;
		this._intervals = [];
		this._anchorIndex = null;
		this._anchorIntervalIndex = null;
	}


	get minIndex(): number {
		return this._minIndex;
	}


	get maxIndex(): number {
		return this._maxIndex;
	}


	get anchorIndex(): number | null {
		return this._anchorIndex;
	}


	get selectedIntervals(): [number, number][] {
		// Return a copy of the intervals list rather than the list itself.
		return this._intervals.map(i => [i[0], i[1]] as [number, number]);
	}


	get selectedIndices(): number[] {
		const indexLists = this._intervals.map(_getIntervalIndices);
		return ([] as number[]).concat(...indexLists);
	}


	get size(): number {
		return this._intervals.reduce(_getSizeAux, 0);
	}


	contains(index: number): boolean {
		return (this._findContainingInterval(index) !== null);
	}


	private _findContainingInterval(index: number): number | null {

		for (let i = 0; i < this._intervals.length; i++)
			if (_contains(this._intervals[i], index))
			    return i;

		// If we get here, no selected interval contains index `index`.
		return null;

	}


	select(index: number) {
        this._intervals = [[index, index]];
        this._anchorIndex = index;
        this._anchorIntervalIndex = 0;
	}


	extend(index: number) {

		const intervals = this._intervals;

		if (this._anchorIndex === null) {

			this._anchorIndex = this._minIndex;
			intervals.push([this._minIndex, index]);

		} else {

            // We assume here that if `this._anchorIndex` is not `null`,
			// then `this._anchorIntervalIndex` is not `null` either.
			const i = this._anchorIntervalIndex!;

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
     *     * `this._anchorIndex` has the correct value (whether `null`
     *       or not), but `this._anchorIntervalIndex` may not.
     *
     * Upon return:
     *
     *     * The intervals of `this._intervals` are disjoint and in
     *       order of increasing start index.
     *
     *     * `this._anchorIndex` is unchanged, and
	 *       `this._anchorIntervalIndex` has the correct corresponding
	 #       value.
     */
	private _normalize() {

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

		if (this.anchorIndex === null)
		    this._anchorIntervalIndex = null;

	}


	toggle(index: number) {

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


function _getSizeAux(acc: number, interval: [number, number]): number {
	const [a, b] = interval;
	return acc + b - a + 1;
}


function _compareIntervals(
	[a0, b0]: [number, number], [a1, b1]: [number, number]
): number {

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


function _contains(v: [number, number], i: number | null): boolean {
	if (i === null)
	    return false
	else
	    return v[0] <= i && i <= v[1];
}


function _combinable(v: [number, number], w: [number, number]): boolean {
	// Caller ensures that v[0] <= w[0].
	return v[1] >= w[0] - 1;
}


function _union(v: [number, number], w: [number, number]): [number, number] {
	// Caller ensures that x[0] <= w[0] and v[1] >= w[0].
	return [v[0], Math.max(v[1], w[1])];
}


function _getIntervalIndices([startIndex, endIndex]: [number, number]) {
	return ArrayUtils.rangeArray(startIndex, endIndex + 1);
}
