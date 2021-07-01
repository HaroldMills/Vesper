import { CommandableOverlay }
    from '/static/vesper/clip-album/commandable-overlay.js';
import { CommandableDelegate }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';


const _COMMAND_SPECS = [
    ['set_time_frequency_point'],
    ['clear_time_frequency_point']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class TimeFrequencyPointOverlay extends CommandableOverlay {


    constructor(clipView, settings) {
        
        super(
            clipView, settings, 'Time-Frequency Point Overlay',
            _commandableDelegate)
            
        this.timeAnnotationName = settings.timeAnnotationName;
        this.frequencyAnnotationName = settings.frequencyAnnotationName;
        this.markerType = settings.markerType;
        
        if (this.markerType === undefined)
            this.markerType = 'Plus Sign';
        
    }


    _executeSetTimeFrequencyPointCommand(env) {

        const clip = this.clipView.clip;
        const startIndex = clip.startIndex;
        
        if (startIndex === null) {
            // clip start index unknown
            
            window.alert(
                `Cannot annotate clip because its start index is ` +
                `unknown.`);
        
        } else {
            
            const event = this.clipView.lastMouseEvent;
            const [time, freq] = this.clipView.getMouseTimeAndFrequency(event);

            const index = startIndex + Math.round(time * clip.sampleRate);
            
            const annotations = new Map([
                [this.timeAnnotationName, index],
                [this.frequencyAnnotationName, freq]
            ]);
            
            this.clipAlbum._annotateClips([clip], annotations);
            
        }

    }


    _executeClearTimeFrequencyPointCommand(env) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set(
            [this.timeAnnotationName, this.frequencyAnnotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        // console.log(
        //     `TimeFrequencyPointOverlay.render ${annotations} ` +
        //     `${this.timeAnnotationName} ${this.frequencyAnnotationName}`);

        if (annotations !== null &&
                annotations.has(this.timeAnnotationName) &&
                annotations.has(this.frequencyAnnotationName)) {

            const index = parseInt(annotations.get(this.timeAnnotationName));
            const freq = 
                parseFloat(annotations.get(this.frequencyAnnotationName));

            this._render(index, freq);

        }

    }


    _render(index, freq) {

        const clipView = this.clipView;
        const clip = clipView.clip;

        if (clip.startIndex === null) 
            // clip start index unknown

            return;
        
        const sampleRate = clip.sampleRate;
        const canvas = clipView.overlayCanvas;

        const time = (index - clip.startIndex) / clip.sampleRate;
        const startTime = 0;
        const endTime = clip.span;
        const x = Math.round(TimeFrequencyUtils.timeToViewX(
            time, startTime, endTime, canvas.width)) + .5;

        const [startFreq, endFreq] = TimeFrequencyUtils.getFreqRange(
            clipView.settings.spectrogram.display, sampleRate / 2.);
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
        
        if (this.markerType === 'Crosshairs') {
            
            // Draw crosshairs through point.
            context.moveTo(x, 0);
            context.lineTo(x, canvas.height);
            context.moveTo(0, y);
            context.lineTo(canvas.width, y);
            
        } else if (this.markerType === null) {
            
            // Draw nothing.
            
        } else {
            
            // Draw plus sign centered on point.
            context.moveTo(x - delta, y);
            context.lineTo(x + delta, y);
            context.moveTo(x, y - delta);
            context.lineTo(x, y + delta);
            
        }
        
        context.stroke();

    }


}
