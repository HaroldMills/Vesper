import { CommandableOverlay }
    from '/static/vesper/clip-album/commandable-overlay.js';
import { CommandableDelegate }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';


const _COMMAND_SPECS = [
    ['set_time_frequency_box_upper_left_corner'],
    ['clear_time_frequency_box_upper_left_corner'],
    ['set_time_frequency_box_lower_right_corner'],
    ['clear_time_frequency_box_lower_right_corner'],
    ['clear_time_frequency_box']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class TimeFrequencyBoxOverlay extends CommandableOverlay {


    constructor(clipView, settings) {
        
        super(
            clipView, settings, 'Time-Frequency Box Overlay',
            _commandableDelegate)
            
        this.upperLeftTimeAnnotationName =
            settings.upperLeftTimeAnnotationName;
        this.upperLeftFrequencyAnnotationName =
            settings.upperLeftFrequencyAnnotationName;
        this.lowerRightTimeAnnotationName =
            settings.lowerRightTimeAnnotationName;
        this.lowerRightFrequencyAnnotationName =
            settings.lowerRightFrequencyAnnotationName;
        this.markerType = settings.markerType;
        
        if (this.markerType === undefined)
            this.markerType = 'Crosshairs';
        
    }


    _executeSetTimeFrequencyBoxUpperLeftCornerCommand(env) {
        this._annotateTimeAndFrequency(
            this.upperLeftTimeAnnotationName,
            this.upperLeftFrequencyAnnotationName);
    }


    _annotateTimeAndFrequency(timeAnnotationName, frequencyAnnotationName) {

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
                [timeAnnotationName, index], [frequencyAnnotationName, freq]]);
            
            this.clipAlbum._annotateClips([clip], annotations);
            
        }

    }


    _executeClearTimeFrequencyBoxUpperLeftCornerCommand(env) {
        this._unannotateTimeAndFrequency(
            this.upperLeftTimeAnnotationName,
            this.upperLeftFrequencyAnnotationName);
    }


    _unannotateTimeAndFrequency(timeAnnotationName, frequencyAnnotationName) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set([
            timeAnnotationName, frequencyAnnotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    _executeSetTimeFrequencyBoxLowerRightCornerCommand(env) {
        this._annotateTimeAndFrequency(
            this.lowerRightTimeAnnotationName,
            this.lowerRightFrequencyAnnotationName);
    }


    _executeClearTimeFrequencyBoxLowerRightCornerCommand(env) {
        this._unannotateTimeAndFrequency(
            this.lowerRightTimeAnnotationName,
            this.lowerRightFrequencyAnnotationName);
    }


    _executeClearTimeFrequencyBoxCommand(env) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set([
            this.upperLeftTimeAnnotationName,
            this.upperLeftFrequencyAnnotationName,
            this.lowerRightTimeAnnotationName,
            this.lowerRightFrequencyAnnotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        if (annotations !== null) {
            
            if (annotations.has(this.upperLeftTimeAnnotationName) &&
                    annotations.has(this.upperLeftFrequencyAnnotationName) &&
                    annotations.has(this.lowerRightTimeAnnotationName) &&
                    annotations.has(this.lowerRightFrequencyAnnotationName)) {
                
                const upperLeftIndex = parseInt(annotations.get(
                    this.upperLeftTimeAnnotationName));
                const upperLeftFreq = parseFloat(annotations.get(
                    this.upperLeftFrequencyAnnotationName));
                const lowerRightIndex = parseInt(annotations.get(
                    this.lowerRightTimeAnnotationName));
                const lowerRightFreq = parseFloat(annotations.get(
                    this.lowerRightFrequencyAnnotationName));

                this._renderBox(
                    upperLeftIndex, upperLeftFreq, lowerRightIndex,
                    lowerRightFreq);

            } else if (annotations.has(this.upperLeftTimeAnnotationName) &&
                    annotations.has(this.upperLeftFrequencyAnnotationName)) {

                const index = parseInt(annotations.get(
                    this.upperLeftTimeAnnotationName));
                const freq = parseFloat(annotations.get(
                    this.upperLeftFrequencyAnnotationName));

                this._renderCorner(index, freq);

            } else if (annotations.has(this.lowerRightTimeAnnotationName) &&
                    annotations.has(this.lowerRightFrequencyAnnotationName)) {

                const index = parseInt(annotations.get(
                    this.lowerRightTimeAnnotationName));
                const freq = parseFloat(annotations.get(
                    this.lowerRightFrequencyAnnotationName));
                this._renderCorner(index, freq);

            }

        }

    }


    _renderBox(
        upperLeftIndex, upperLeftFreq, lowerRightIndex, lowerRightFreq
    ) {

        const clipView = this.clipView;

        if (clipView.clip.startIndex === null) 
            // clip start index unknown

            return;
        
        const [startX, endY] =
            this._getCornerXY(upperLeftIndex, upperLeftFreq, clipView);

        const [endX, startY] =
            this._getCornerXY(lowerRightIndex, lowerRightFreq, clipView);

        const width = endX - startX;
        const height = endY - startY;

        const canvas = clipView.overlayCanvas;
        const context = canvas.getContext('2d');

        context.strokeStyle = 'red';
        context.lineWidth = 1;
        context.lineCap = 'butt';
        context.lineStyle = 'solid';

        context.strokeRect(startX, startY, width, height);

    }


    _getCornerXY(index, freq, clipView) {

        const clip = clipView.clip;
        const canvas = clipView.overlayCanvas;

        const time = (index - clip.startIndex) / clip.sampleRate;
        const startTime = 0;
        const endTime = clip.span;
        const x = Math.round(TimeFrequencyUtils.timeToViewX(
            time, startTime, endTime, canvas.width)) + .5;

        const [startFreq, endFreq] = TimeFrequencyUtils.getFreqRange(
            clipView.settings.spectrogram.display, clip.sampleRate / 2.);
        const y = Math.round(TimeFrequencyUtils.freqToViewY(
            freq, startFreq, endFreq, canvas.height)) + .5;

        return [x, y];

    }


    _renderCorner(index, freq) {

        const clipView = this.clipView;

        if (clipView.clip.startIndex === null) 
            // clip start index unknown

            return;
        
        const [x, y] = this._getCornerXY(index, freq, clipView);

        const markerWidth = 11;
        const delta = Math.floor(markerWidth / 2);

        const canvas = clipView.overlayCanvas;
        const context = canvas.getContext('2d');

        context.strokeStyle = 'red';
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
