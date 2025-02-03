import { CommandableOverlay } from './commandable-overlay.js';
import { CommandableDelegate } from './keyboard-input-interpreter.js';
import { TimeFrequencyUtils } from './time-frequency-utils.js';


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
            
        this.startTimeAnnotationName = settings.startTimeAnnotationName;
        this.endFrequencyAnnotationName = settings.endFrequencyAnnotationName;
        this.endTimeAnnotationName = settings.endTimeAnnotationName;
        this.startFrequencyAnnotationName =
            settings.startFrequencyAnnotationName;
        this.markerType = settings.markerType;
        
        if (this.markerType === undefined)
            this.markerType = 'Crosshairs';
        
    }


    _executeSetTimeFrequencyBoxUpperLeftCornerCommand(env) {
        this._annotateTimeAndFrequency(
            this.startTimeAnnotationName, this.endFrequencyAnnotationName);
    }


    _annotateTimeAndFrequency(timeAnnotationName, frequencyAnnotationName) {

        const clip = this.clipView.clip;
        const startIndex = clip.startIndex;
        
        if (startIndex === null) {
            // clip start index unknown
            
            window.alert(
                `Cannot annotate clip because its start index is unknown.`);
        
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
            this.startTimeAnnotationName, this.endFrequencyAnnotationName);
    }


    _unannotateTimeAndFrequency(timeAnnotationName, frequencyAnnotationName) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set([
            timeAnnotationName, frequencyAnnotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    _executeSetTimeFrequencyBoxLowerRightCornerCommand(env) {
        this._annotateTimeAndFrequency(
            this.endTimeAnnotationName, this.startFrequencyAnnotationName);
    }


    _executeClearTimeFrequencyBoxLowerRightCornerCommand(env) {
        this._unannotateTimeAndFrequency(
            this.endTimeAnnotationName, this.startFrequencyAnnotationName);
    }


    _executeClearTimeFrequencyBoxCommand(env) {
        const clips = [this.clipView.clip];
        const annotationNames = new Set([
            this.startTimeAnnotationName,
            this.endFrequencyAnnotationName,
            this.endTimeAnnotationName,
            this.startFrequencyAnnotationName]);
        this.clipAlbum._unannotateClips(clips, annotationNames);
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        if (annotations !== null) {
            
            if (annotations.has(this.startTimeAnnotationName) &&
                    annotations.has(this.endFrequencyAnnotationName) &&
                    annotations.has(this.endTimeAnnotationName) &&
                    annotations.has(this.startFrequencyAnnotationName)) {
                
                const upperLeftIndex = parseInt(annotations.get(
                    this.startTimeAnnotationName));
                const upperLeftFreq = parseFloat(annotations.get(
                    this.endFrequencyAnnotationName));
                const lowerRightIndex = parseInt(annotations.get(
                    this.endTimeAnnotationName));
                const lowerRightFreq = parseFloat(annotations.get(
                    this.startFrequencyAnnotationName));

                this._renderBox(
                    upperLeftIndex, upperLeftFreq, lowerRightIndex,
                    lowerRightFreq);

            } else if (annotations.has(this.startTimeAnnotationName) &&
                    annotations.has(this.endFrequencyAnnotationName)) {

                const index = parseInt(annotations.get(
                    this.startTimeAnnotationName));
                const freq = parseFloat(annotations.get(
                    this.endFrequencyAnnotationName));

                this._renderCorner(index, freq);

            } else if (annotations.has(this.endTimeAnnotationName) &&
                    annotations.has(this.startFrequencyAnnotationName)) {

                const index = parseInt(annotations.get(
                    this.endTimeAnnotationName));
                const freq = parseFloat(annotations.get(
                    this.startFrequencyAnnotationName));
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
