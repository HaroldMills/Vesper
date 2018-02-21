import { ArrayUtils } from '../util/array-utils.js';
export class Multiselection {
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
        }
        else {
            const i = this._anchorIntervalIndex;
            if (index <= this._anchorIndex)
                intervals[i] = [index, this._anchorIndex];
            else
                intervals[i] = [this._anchorIndex, index];
        }
        this._normalize();
    }
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
    toggle(index) {
        const intervals = this._intervals;
        const i = this._findContainingInterval(index);
        if (i === null) {
            intervals.push([index, index]);
            this._anchorIndex = index;
            this._normalize();
        }
        else {
            const [a, b] = intervals[i];
            if (a !== b) {
                intervals.splice(i, 1);
                if (index === b) {
                    intervals.push([a, b - 1]);
                    this._anchorIndex = index - 1;
                }
                else {
                    if (index !== a)
                        intervals.push([a, index - 1]);
                    intervals.push([index + 1, b]);
                    this._anchorIndex = index + 1;
                }
                this._normalize();
            }
            else {
                if (i !== intervals.length - 1)
                    this._anchorIndex = intervals[i + 1][0];
                else if (i !== 0)
                    this._anchorIndex = intervals[i - 1][1];
                else
                    this._anchorIndex = null;
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
    if (i === null)
        return false;
    else
        return v[0] <= i && i <= v[1];
}
function _combinable(v, w) {
    return v[1] >= w[0] - 1;
}
function _union(v, w) {
    return [v[0], Math.max(v[1], w[1])];
}
function _getIntervalIndices([startIndex, endIndex]) {
    return ArrayUtils.rangeArray(startIndex, endIndex + 1);
}
