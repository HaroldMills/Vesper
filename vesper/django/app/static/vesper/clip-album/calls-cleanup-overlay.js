import { CommandableOverlay }
    from '/static/vesper/clip-album/commandable-overlay.js';
import { CommandableDelegate }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';


const _COMMAND_SPECS = [
    ['exclude_call_clip'],
    ['include_call_clip']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


/*
 * Spectrogram view overlay for manual cleanup of Old Bird call detections
 * for machine learning datasets.
 * 
 * This overlay shades a spectrogram time interval extending from the
 * `startTime` setting to the `endTime` setting. Both times are
 * specified in units of seconds from the start of the clip.
 * 
 * The overlay has two commands, one called `exclude_call_clip` that
 * reclassifies a Call[.<subclass>] clip to XCall[.<subclass>] (that
 * is, preserving any subclass information in the original classification),
 * and another called `include_call_clip` that reclassifies an
 * XCall[.<subclass>] clip to Call[.<subclass>]. Note that two commands
 * are inverses.
 */
export class CallsCleanupOverlay extends CommandableOverlay {


    constructor(clipView, settings) {
        
        super(
            clipView, settings, 'Calls Cleanup Overlay', _commandableDelegate)
            
        this.annotationName = 'Classification';
        this.callClass = 'Call';
        this.excludedCallClass = 'XCall';
        
    }


    _executeExcludeCallClipCommand(env) {
        this._reclassifyCallClip(this.callClass, this.excludedCallClass);
    }
    
    
    _reclassifyCallClip(fromCoarseClass, toCoarseClass) {
        
        const clip = this.clipView.clip;
        const classification = clip.annotations.get(this.annotationName);
        
        if (classification !== undefined &&
                classification.startsWith(fromCoarseClass)) {
            
            const newClassification =
                classification.replace(fromCoarseClass, toCoarseClass);
            
            const annotations = new Map([
                [this.annotationName, newClassification]
            ]);
                       
            this.clipAlbum._annotateClips([clip], annotations);
            
        }
        
    }


    _executeIncludeCallClipCommand(env) {
        this._reclassifyCallClip(this.excludedCallClass, this.callClass);
    }
    
    
    render() {

        const clipView = this.clipView;
        const clip = clipView.clip;

        const sampleRate = clip.sampleRate;
        const canvas = clipView.overlayCanvas;

        const settings = this.settings;
        const startX = TimeFrequencyUtils.timeToViewX(
            settings.startTime, 0, clip.span, canvas.width);
        const endX = TimeFrequencyUtils.timeToViewX(
            settings.endTime, 0, clip.span, canvas.width);
        const width = endX - startX;
        
        const context = canvas.getContext('2d');

        context.fillStyle = 'rgba(255, 165, 0, .25)';
        context.rect(startX, 0, width, canvas.height);
        context.fill();
        
    }


}
