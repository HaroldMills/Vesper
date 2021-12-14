/**
 * Auto-advancer, which asynchronously invokes a handler on each of
 * a sequence of integers with pauses inbetween.
 */


import { Pauser } from '/static/vesper/util/pauser.js';


 export class AutoAdvancer {


    constructor(indexHandler, pause, minPause, maxPause, pauseScaleFactor) {
        this._state = AutoAdvancerState.Stopped;
        this._startIndex = null;
        this._endIndex = null;
        this._indexHandler = indexHandler;
        this._pause = pause;
        this._minPause = minPause;
        this._maxPause = maxPause;
        this._pauseScaleFactor = pauseScaleFactor;
    }


    get state() {
        return this._state;
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

        if (this.state === AutoAdvancerState.Stopped) {

            this._state = AutoAdvancerState.Running;

            for (let i = startIndex; i !== endIndex; i++) {

                // Handle index `i`.
                await this._indexHandler(i);

                // Break if `stop` method was called during index handling.
                if (this.state === AutoAdvancerState.Stopping)
                    break;
    
                // Pause.
                this._pauser = new Pauser(this.pause);
                await this._pauser.pause();
                this._pauser = null;

                // Break if `stop` method was called during pause.
                if (this.state === AutoAdvancerState.Stopping)
                    break;
    
            }

            this._state = AutoAdvancerState.Stopped;

        }

    }


    stop() {

        if (this.state === AutoAdvancerState.Running) {

            this._state = AutoAdvancerState.Stopping;

            // Cancel pause if in progress.
            if (this._pauser !== null)
                this._pauser.cancel();

        }

    }


    decreasePause() {
        if (this.state === AutoAdvancerState.Running)
            this._scalePause(1 / this._pauseScaleFactor);
    }


    _scalePause(factor) {
        const pause = factor * this._pause;
        this._pause = this._clipPauseIfNeeded(pause);
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
        if (this.state === AutoAdvancerState.Running)
            this._scalePause(this._pauseScaleFactor);
    }


}


export class AutoAdvancerState {

    static Stopped = new AutoAdvancerState('Stopped');
    static Running = new AutoAdvancerState('Running');
    static Stopping = new AutoAdvancerState('Stopping');

    constructor(name) {
        this._name = name;
    }

    get name() {
        return this._name;
    }

    toString() {
        return this.name;
    }

}
