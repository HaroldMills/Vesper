// I wrote this in JavaScript, following the style of array-utils.js,
// which was translated from TypeScript. We might eventually want to
// use TypeScript for this module, too.


export var ViewUtils;

(function (ViewUtils) {

    // Handles clip filter parameter value changes made via the set
    // clip filter modal. The set clip filter modal can be invoked
    // from both clip calendars and clip albums.
    function onSetClipFilterModalOkButtonClick(event) {
    
        // Get current URL and clip filter.
        const url = new URL(window.location.href);
        const params = url.searchParams;
        const stationMic = params.get('station_mic');
        const detector = params.get('detector');
        const classification = params.get('classification');
        const tag = params.get('tag');
        
        // Get new clip filter.
        const newStationMic = document.getElementById(
            'set-clip-filter-modal-station-mic-select').value;
        const newDetector = document.getElementById(
            'set-clip-filter-modal-detector-select').value;
        const newClassification = document.getElementById(
            'set-clip-filter-modal-classification-select').value;
        const newTag = document.getElementById(
            'set-clip-filter-modal-tag-select').value;
        
        if (newStationMic == stationMic &&
                newDetector == detector &&
                newClassification == classification &&
                newTag == tag) {
                // new clip filter is same as current one
            
            // Reload page to reflect possible changes to clip metadata.
            window.location.reload();
            
        } else {
            // new clip filter differs from current one
            
            // Update clip filter in URL.
            params.set('station_mic', newStationMic);
            params.set('detector', newDetector);
            params.set('classification', newClassification);
            params.set('tag', newTag);
            params.set('page', 1);
            
            // Go to new URL.
            window.location.href = url.href;
            
        }
    
    }

    ViewUtils.onSetClipFilterModalOkButtonClick =
        onSetClipFilterModalOkButtonClick;
    
})(ViewUtils || (ViewUtils = {}));
