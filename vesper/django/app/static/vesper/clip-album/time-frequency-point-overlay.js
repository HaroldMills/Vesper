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

        const e = this.clipView.lastMouseEvent;
        const tf = this.clipView.getMouseTimeAndFrequency(e);

        if (tf !== null)
            this._setTimeFrequencyAnnotations(...tf);

    }


    _setTimeFrequencyAnnotations(time, frequency) {

        const clip = this.clipView.clip;
        const startIndex = clip.startIndex;
        
        if (startIndex === null)
            // clip start index unknown
            
            return;
            
        const index = startIndex + Math.round(time * clip.sampleRate);
        
        const url = `/clips/${clip.id}/annotations/json/`;

        const annotations = new Object();
        annotations[this.timeAnnotationName] = index;
        annotations[this.frequencyAnnotationName] = frequency;

        this._postJson(url, annotations)
        .then(r => this._onAnnotationsPostFulfilled(r, annotations))
        .catch(this._onAnnotationsPostRejected);

    }


    _postJson(url, object) {

        return fetch(url, {
            method: 'POST',
            body: JSON.stringify(object),
            headers: new Headers({
                'Content-Type': 'application/json; charset=utf-8'
            }),
            credentials: 'same-origin'
        });

    }


    _onAnnotationsPostFulfilled(response, annotations) {

        if (response.status === 200) {
            // Update clip annotations and re-render.

            const clip = this.clipView.clip;
            const clip_annos = clip.annotations;

            if (clip_annos !== null) {
                // client has received clip annotations from server

                for (const name of Object.getOwnPropertyNames(annotations)) {

                    const value = annotations[name];

                    if (value === null)
                        delete clip_annos[name]
                    else
                        clip_annos[name] = value;

                }

            } else {
                // client has not yet received clip annotations from server

               // TODO: Not sure what we should do here. We can't
               // update annotations we haven't yet received. Perhaps
               // we should decline to post annotation changes until
               // we have received the original annotations from the
               // server.

            }

            clip.view.render();

        } else {

            window.alert(
                `Clip annotation request failed with response ` +
                `${response.status} (${response.statusText}).`);

        }

    }


    _onAnnotationsPostRejected(error) {
        window.alert(
            `Clip annotation request failed with exception: ` +
            `${error.message}.`);
    }


    _executeClearTimeFrequencyPointCommand(env) {
        this._setTimeFrequencyAnnotations(null, null);
    }


    render() {

        const annotations = this.clipView.clip.annotations;

        // console.log(
        //     `TimeFrequencyPointOverlay.render ${annotations} ` +
        //     `${this.timeAnnotationName} ${this.frequencyAnnotationName}`);

        if (annotations !== null &&
                annotations.hasOwnProperty(this.timeAnnotationName) &&
                annotations.hasOwnProperty(this.frequencyAnnotationName)) {

            const index = parseInt(annotations[this.timeAnnotationName]);
            const freq = parseFloat(annotations[this.frequencyAnnotationName]);

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
