import { CommandableOverlay }
    from '/static/vesper/clip-album/commandable-overlay.js';
import { CommandableDelegate }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';


const _COMMAND_SPECS = [
    ['set_time_point'],
    ['clear_time_point']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class TimePointOverlay extends CommandableOverlay {


    constructor(clipView, settings) {
        super(clipView, settings, 'Time Point Overlay', _commandableDelegate)
        this.annotationName = settings.annotationName;
    }


    _executeSetTimePointCommand(env) {

        const clip = this.clipView.clip;
        const startIndex = clip.startIndex;
        
        if (startIndex === null) {
            // clip start index unknown
            
            window.alert(
                `Cannot annotate clip because its start index is ` +
                `unknown.`);
        
        } else {
            
            const event = this.clipView.lastMouseEvent;
            const time = this.clipView.getMouseTimeAndFrequency(event)[0];
            const index = startIndex + Math.round(time * clip.sampleRate);
            const annotations = new Map([[this.annotationName, index]]);
            
            this.clipAlbum._annotateClips([clip], annotations);
            
        }

    }


    _executeClearTimePointCommand(env) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set([this.annotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        // console.log(
        //     `TimePointOverlay.render ${annotations} ` +
        //     `${this.annotationName}`);

        if (annotations !== null && annotations.has(this.annotationName)) {

            const index = parseInt(annotations.get(this.annotationName));
            this._render(index);

        }

    }


    _render(index) {

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

        const context = canvas.getContext('2d');

        context.strokeStyle = 'orange';
        context.lineWidth = 1;
        context.lineCap = 'butt';
        context.lineStyle = 'solid';

        context.beginPath();
        context.moveTo(x, 0);
        context.lineTo(x, canvas.height);
        context.stroke();

    }


}
