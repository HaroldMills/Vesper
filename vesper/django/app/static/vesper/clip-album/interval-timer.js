export class IntervalTimer {


    constructor(
            interval, minInterval, maxInterval, intervalScaleFactor,
            callback) {

        this._running = false;
        this._interval = interval;
        this._minInterval = minInterval;
        this._maxInterval = maxInterval;
        this._intervalScaleFactor = intervalScaleFactor;
        this._callback = callback;

    }


    start() {
        if (!this._running) {
            this._running = true;
            this._setTimeout();
        }
    }


    _setTimeout() {
        this._timeoutId = setTimeout(
            () => this._onTimeout(),
            1000 * this._interval);
    }


    _onTimeout() {

        const stop = this._callback();

        if (stop)
            this._running = false;
        else
            this._setTimeout();

    }

  
    stop() {
        if (this._running) {
            clearTimeout(this._timeoutId);
            this._running = false;
        }
    }


    toggle() {
        if (this._running)
            this.stop();
        else
            this.start();
    }


    decreaseInterval() {
        this._scaleInterval(1 / this._intervalScaleFactor);
    }


    _scaleInterval(factor) {
        if (this._running) {
            const interval = factor * this._interval;
            this._interval = this._clipIntervalIfNeeded(interval);
        }
    }


    _clipIntervalIfNeeded(interval) {
        if (this._minInterval !== null && interval < this._minInterval)
            return this._minInterval;
        else if (this._maxInterval !== null && interval > this._maxInterval)
            return this._maxInterval;
        else
            return interval;
    }


    increaseInterval() {
        this._scaleInterval(this._intervalScaleFactor);
    }


}
