import { CommandableDelegate }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';


const _COMMAND_SPECS = [
    ['set_time_frequency_point'],
    ['clear_time_frequency_point']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class TimeFrequencyPointOverlay {


    constructor(clipView, settings) {
        this.clipView = clipView;
        this.commandableName = this._getCommandableName(settings);
        this._commandableDelegate = _commandableDelegate;
        this.timeAnnotationName = settings.timeAnnotationName;
        this.frequencyAnnotationName = settings.frequencyAnnotationName;
    }


    _getCommandableName(settings) {
        if (settings.name === undefined)
            return 'Time-Frequency Point Overlay';
        else
            return settings.name;
    }


    hasCommand(commandName) {
        return this._commandableDelegate.hasCommand(commandName);
    }


    executeCommand(command, env) {
        this._commandableDelegate.executeCommand(command, this, env);
    }


    _executeSetTimeFrequencyPointCommand(env) {
        console.log('set time frequency point');
    }


    _executeClearTimeFrequencyPointCommand(env) {
        console.log('clear time frequency point');
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        // console.log(
        //     `TimeFrequencyPointOverlay.render ${annotations} ` +
        //     `${this.timeAnnotationName} ${this.frequencyAnnotationName}`);

        if (annotations !== null &&
                annotations.hasOwnProperty(this.timeAnnotationName) &&
                annotations.hasOwnProperty(this.frequencyAnnotationName)) {

            const time = parseFloat(annotations[this.timeAnnotationName]);
            const freq = parseFloat(annotations[this.frequencyAnnotationName]);

            // console.log('TimeFrequencyPointOverlay.render', time, freq);

            this._render(time, freq);

        }

    }


    _render(time, freq) {

        const clipView = this.clipView;
        const clip = clipView.clip;
        const sampleRate = clip.sampleRate;
        const canvas = clipView.overlayCanvas;

        const startTime = 0;
        const endTime = clip.span;
        const x = Math.round(TimeFrequencyUtils.timeToViewX(
            time, startTime, endTime, canvas.width)) + .5;

        const [startFreq, endFreq] = TimeFrequencyUtils.getFreqRange(
            clipView.settings.spectrogram, sampleRate / 2.);
        const y = Math.round(TimeFrequencyUtils.freqToViewY(
            freq, startFreq, endFreq, canvas.height)) + .5;

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
