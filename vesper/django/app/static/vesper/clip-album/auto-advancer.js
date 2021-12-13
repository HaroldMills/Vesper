/**
 * Auto-advancer, which asynchronously invokes a handler on each of
 * a sequence of integers with pauses inbetween.
 */


export class AutoAdvancer {


    constructor(indexHandler, pause, minPause, maxPause, pauseScaleFactor) {
        this._running = false;
        this._startIndex = null;
        this._endIndex = null;
        this._indexHandler = indexHandler;
        this._pause = pause;
        this._minPause = minPause;
        this._maxPause = maxPause;
        this._pauseScaleFactor = pauseScaleFactor;
    }


    get running() {
        return this._running;
    }


    get startIndex() {
        return this._startIndex;
    }


    get endIndex() {
        return this._endIndex;
    }


    get pause() {
        return this._pause;
    }


    get minPause() {
        return this._minPause;
    }


    get maxPause() {
        return this._maxPause;
    }


    get pauseScaleFactor() {
        return this._pauseScaleFactor;
    }


    async start(startIndex, endIndex) {

        if (!this._running) {

            this._running = true;

            for (let i = startIndex; i !== endIndex; i++) {

                if (!this._running)
                    // auto-advance has been stopped

                    break;
    
                await this._indexHandler(i);
    
                await _pause(this._pause);
    
            }

            this.stop();

        }

    }


    stop() {
        if (this._running)
            this._running = false;
    }


    decreasePause() {
        this._scalePauseIfRunning(1 / this._pauseScaleFactor);
    }


    _scalePauseIfRunning(factor) {
        if (this._running) {
            const pause = factor * this._pause;
            this._pause = this._clipPauseIfNeeded(pause);
        }
    }


    _clipPauseIfNeeded(pause) {
        if (this._minPause !== null && pause < this._minPause)
            return this._minPause;
        else if (this._maxPause !== null && pause > this._maxPause)
            return this._maxPause;
        else
            return pause;
    }


    increasePause() {
        this._scalePauseIfRunning(this._pauseScaleFactor);
    }


}


function _pause(duration) {
    return new Promise(
        (resolve, reject) => setTimeout(resolve, 1000 * duration)
    );
}
