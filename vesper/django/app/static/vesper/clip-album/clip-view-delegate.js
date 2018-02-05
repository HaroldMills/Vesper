'use strict'


export class ClipViewDelegate {


	// TODO: Some clip view delegates will want to respond to mouse
	// and keyboard events, e.g. to allow clip metadata creation like
	// call start and end times and/or frequencies or frequency tracks.
	// Figure out how this will work and create a view delegate that
	// demonstrates it.

	// TODO: Can we use BokehJS to plot in a clip view? BokehJS might
	// create the entire contents, or it might just create an overlay
	// that is drawn on top of contents that are rendered otherwise.


	constructor(clipView, clip, settings) {
		this._clipView = clipView;
		this._clip = clip;
		this._settings = settings;
	}


	get clipView() {
		return this._clipView;
	}


	get clip() {
		return this._clip;
	}


	get settings() {
		return this._settings;
	}


	set settings(settings) {
		this._settings = settings;
	}


	/**
	 * Updates the canvas of this delegate's clip view after the clip's
	 * samples have changed.
	 *
	 * The canvas is available from this method as `this.clipView._canvas`,
	 * the clip's audio data are available as `this.clip.audioBuffer`
	 * (a Web Audio `AudioBuffer`), and the clip's samples are available as
	 * `this.clip.samples`, a `Float32Array`.
	 *
	 * Note that the clip's samples may have changed by becoming unavailable,
	 * in which case `this.clip.audioBuffer` and `this.clip.samples` will
	 * both be `null`.
	 */
	onClipSamplesChanged() {
		throw new Error(
			'ClipViewDelegate.onClipSamplesChanged not implemented');
	}


	/**
	 * Renders the contents of this delegate's clip view.
	 *
	 * This method is invoked by a delegate's clip view whenever the
	 * contents of the clip view may need to be rendered, including
	 * when the containing clip album has changed size.
	 */
	render() {
		throw new Error('ClipViewDelegate.render method not implemented.');
	}


	/**
	 * Gets text to display for the current mouse position.
	 *
	 * This method is invoked by a delegate's clip view whenever the
	 * mouse enters, leaves, or moves within the view. The argument is
	 * the mouse event that triggered the invocation, along with an
	 * event name that is either "mouseenter", "mouseleave", or
	 * "mousemove". The method can return either text to display
	 * instead of the view's usual label, or `null` to display the
	 * usual label.
	 */
	getMouseText(event, name) {
		return null;
	}


}
