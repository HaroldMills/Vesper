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

// default rendering setting values
const _DEFAULT_BOX_COLOR = 'magenta';
const _DEFAULT_BOX_LINE_WIDTH = 2;
const _DEFAULT_MOUSE_CROSSHAIR_COLOR = 'red';
const _DEFAULT_MOUSE_CROSSHAIR_LINE_WIDTH = 1;
const _DEFAULT_MOUSE_CROSSHAIR_LINE_DASH = [10, 5];


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

        this.boxColor = this._getSettingValue(
            settings.boxColor, _DEFAULT_BOX_COLOR);

        this.boxLineWidth = this._getSettingValue(
            settings.boxLineWidth, _DEFAULT_BOX_LINE_WIDTH);

        this.mouseCrosshairColor = this._getSettingValue(
            settings.mouseCrosshairColor, _DEFAULT_MOUSE_CROSSHAIR_COLOR);

        this.mouseCrosshairLineWidth = this._getSettingValue(
            settings.mouseCrosshairLineWidth,
            _DEFAULT_MOUSE_CROSSHAIR_LINE_WIDTH);

        this.mouseCrosshairLineDash = this._getSettingValue(
            settings.mouseCrosshairLineDash,
            _DEFAULT_MOUSE_CROSSHAIR_LINE_DASH);

        // Install mouse event listeners on overlay canvas for drawing
        // crosshairs.
        const canvas = this.clipView.overlayCanvas;
        canvas.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    canvas.addEventListener('mousemove', e => this._onMouseMove(e));
	    canvas.addEventListener('mouseleave', e => this._onMouseLeave(e));
        this._canvas = canvas;

        this._mouseX = null;
        this._mouseY = null;
        
    }


    _getSettingValue(value, defaultValue) {
        return value !== undefined ? value : defaultValue;
    }


    _onMouseEnter(e) {
        // console.log(`mouse enter ${e.clientX} ${e.clientY}`);
        this._stashCursor();
        this._updateMousePosition(e);
        this.clipView._renderOverlays();
    }


    _stashCursor() {
        this._cursor = this.clipView.overlayCanvas.style.cursor;
        this.clipView.overlayCanvas.style.cursor = 'none';
    }


    _updateMousePosition(e) {
        const rect = this._canvas.getBoundingClientRect();
        this._mouseX = e.clientX - rect.left;
        this._mouseY = e.clientY - rect.top;
        this.clipView.getMouseTimeAndFrequency(e);
    }


    _onMouseMove(e) {
        // console.log(`mouse move ${e.clientX} ${e.clientY}`);
        this._updateMousePosition(e);
        this.clipView._renderOverlays();
        this.clipView.getMouseTimeAndFrequency(e);
    }


    _onMouseLeave(e) {
        // console.log(`mouse leave ${e.clientX} ${e.clientY}`);
        this._restoreCursor();
        this._mouseX = null;
        this._mouseY = null;
        this.clipView._renderOverlays();
    }


    _restoreCursor() {
        this.clipView.overlayCanvas.style.cursor = this._cursor;
    }


    _executeSetTimeFrequencyBoxUpperLeftCornerCommand(env) {
        this._annotateTimeAndFrequency(
            this.startTimeAnnotationName, this.endFrequencyAnnotationName);
    }


    _annotateTimeAndFrequency(timeAnnotationName, frequencyAnnotationName) {

        const clipView = this.clipView
        const clip = clipView.clip;
        const startIndex = clip.startIndex;
        
        if (startIndex === null) {
            // clip start index unknown
            
            window.alert(
                `Cannot annotate clip because its start index is unknown.`);
        
        } else {
            
            const event = clipView.lastMouseEvent;
            const [time, freq] = clipView.getMouseTimeAndFrequency(event);

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

            this._renderMouseCrosshairs();

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
            this._getCornerXY(upperLeftIndex, upperLeftFreq);

        const [endX, startY] =
            this._getCornerXY(lowerRightIndex, lowerRightFreq);

        const width = endX - startX;
        const height = endY - startY;

        const canvas = clipView.overlayCanvas;
        const context = canvas.getContext('2d');

        context.strokeStyle = this.boxColor;
        context.lineWidth = this.boxLineWidth;
        context.setLineDash([]);
        context.lineCap = 'butt';

        context.strokeRect(startX, startY, width, height);

    }


    _getCornerXY(index, freq) {

        const clipView = this.clipView;
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

        if (this.clipView.clip.startIndex === null) 
            // clip start index unknown

            return;
        
        const [x, y] = this._getCornerXY(index, freq);

        this._renderCrosshairs(x, y, this.boxColor, this.crosshairLineWidth);

    }


    _renderCrosshairs(x, y, color, lineWidth, lineDash = []) {

        const canvas = this.clipView.overlayCanvas;
        const context = canvas.getContext('2d');

        context.strokeStyle = color;
        context.lineWidth = lineWidth;
        context.setLineDash(lineDash);
        context.lineCap = 'butt';

        context.beginPath();
        context.moveTo(x, 0);
        context.lineTo(x, canvas.height);
        context.moveTo(0, y);
        context.lineTo(canvas.width, y);
        context.stroke();

    }


    _renderMouseCrosshairs() {
        if (this._mouseX !== null) {
            this._renderCrosshairs(
                this._mouseX, this._mouseY, this.mouseCrosshairColor,
                this.mouseCrosshairLineWidth, this.mouseCrosshairLineDash);
        }
    }


}
