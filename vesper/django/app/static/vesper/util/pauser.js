/**
 * Cancelable, promise-based pauser.
 * 
 * We could also implement cancelable, promise-based pauses with a
 * `pause` function that returns a `Promise` on which we have set
 * (i.e. "monkey-patched") a `cancel` function (for details on that
 * and other approaches, see https://stackoverflow.com/questions/25345701/
 * how-to-cancel-timeout-inside-of-javascript-promise), but I prefer
 * this form.
 */
 export class Pauser {

    /**
     * Pauses for a specified duration, without the option of canceling.
     */
    static async pause(duration) {
        const pauser = new Pauser(duration);
        await pauser.pause();
    }

    constructor(duration) {
        this._duration = duration;
        this._pauseCalled = false;
        this._resolve = null;
    }

    get duration() {
        return this._duration;
    }

    pause() {

        if (this._pauseCalled) {
            throw new Error('Attempt to call Pauser.pause more than once.');
        }

        this._pauseCalled = true;

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

        if (!this._pauseCalled) {
            throw new Error('Pauser.cancel called before Pauser.pause.');
        }

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
