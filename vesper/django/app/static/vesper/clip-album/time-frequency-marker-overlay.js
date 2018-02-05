'use strict'


import * as TFU from '/static/vesper/clip-album/time-frequency-utils.js';


export class TimeFrequencyMarkerOverlay {


    constructor(parent, timeAnnotationName, freqAnnotationName) {
        this.parent = parent;
        this.timeAnnotationName = timeAnnotationName;
        this.freqAnnotationName = freqAnnotationName;
    }


    render() {

        const annotations = this.parent.clip.annotations;

        if (annotations !== null &&
                annotations.hasOwnProperty(this.timeAnnotationName) &&
                annotations.hasOwnProperty(this.freqAnnotationName)) {

            const time = parseFloat(annotations[this.timeAnnotationName]);
            const freq = parseFloat(annotations[this.freqAnnotationName]);

            // console.log('TimeFrequencyMarkerOverlay.render', time, freq);

            this._render(time, freq);

        }

    }


    _render(time, freq) {

        const clipView = this.parent;
        const clip = clipView.clip;
        const sampleRate = clip.sampleRate;
        const canvas = clipView.overlayCanvas;

        const startTime = 0;
        const endTime = clip.span;
        const x = Math.round(
            TFU.timeToViewX(time, startTime, endTime, canvas.width)) + .5;

        const [startFreq, endFreq] =
            TFU.getFreqRange(clipView.settings.spectrogram, sampleRate / 2.);
        const y = Math.round(
            TFU.freqToViewY(freq, startFreq, endFreq, canvas.height)) + .5;

        const markerWidth = 11;
        const delta = Math.floor(markerWidth / 2);

        const context = canvas.getContext('2d');

        context.strokeStyle = 'orange';
        context.lineWidth = 1;
        context.lineCap = 'butt';
        context.lineStyle = 'solid';

        context.beginPath();
        context.moveTo(x - delta, y);
        context.lineTo(x + delta, y);
        context.moveTo(x, y - delta);
        context.lineTo(x, y + delta);
        context.stroke();

    }


}
