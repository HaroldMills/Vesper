/**
 * Cancellable, promise-based pauser.
 * 
 * We could also implement cancellable, promise-based pauses with a
 *  `pause` function that returns a `Promise` on which we have set a
 * `cancel` function, but I prefer this form.
 */
 export class Pauser {

    constructor(duration) {
        this._duration = duration;
        this._resolve = null;
    }

    get duration() {
        return this._duration;
    }

    pause() {
        return new Promise(
            (resolve, reject) => this._setTimeout(resolve, this._duration)
        )
    }

    _setTimeout(resolve, duration) {

        // Save `resolve` function so it's available to the `cancel`
        // method. 
        this._resolve = resolve;

        // Set up timeout to call `resolve` function. Save timeout
        // ID so it's available to the `cancel` method.
        this._timeoutId = setTimeout(resolve, 1000 * duration);

    }

    cancel() {

        if (this._resolve !== null) {
            // have a resolve function

            // I think this isn't necessary since calling `resolve` twice
            // (once from this method and again later when the timeout
            // occurred) would be harmless, but this seems like better
            // form.
            clearTimeout(this._timeoutId);

            // We resolve on cancel instead of rejecting since we don't
            // consider cancellation to be an error condition.
            this._resolve();

        }

    }

}
