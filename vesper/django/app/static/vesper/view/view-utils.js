// I wrote this in JavaScript, following the style of array-utils.js,
// which was translated from TypeScript. We might eventually want to
// use TypeScript for this module, too.


export var ViewUtils;

(function (ViewUtils) {

    // Handles clip filter parameter value changes made via the
    // filter clips modal. The filter clips modal can be invoked
    // from both clip calendars and clip albums.
    function onFilterClipsModalOkButtonClick(event) {
    
        // Get current URL and clip filter.
        const url = new URL(window.location.href);
        const params = url.searchParams;
        const stationMic = params.get('station_mic');
        const detector = params.get('detector');
        const classification = params.get('classification');
        // const tag = params.get('tag');
        
        // Get new clip filter.
        const newStationMic = document.getElementById(
            'filter-clips-modal-station-mic-select').value;
        const newDetector = document.getElementById(
            'filter-clips-modal-detector-select').value;
        const newClassification = document.getElementById(
            'filter-clips-modal-classification-select').value;
        // const newTag = document.getElementById(
        //     'filter-clips-modal-tag-select').value;
        
        if (newStationMic !== stationMic ||
                newDetector !== detector ||
                newClassification !== classification) { // ||
                // newTag !== tag) {
                // new clip filter differs from current one
            
            // Update clip filter in URL.
            params.set('station_mic', newStationMic);
            params.set('detector', newDetector);
            params.set('classification', newClassification);
            // params.set('tag', newTag);
            
            // Go to new URL.
            window.location.href = url.href;
            
        }
    
    }

    ViewUtils.onFilterClipsModalOkButtonClick =
        onFilterClipsModalOkButtonClick;
    
})(ViewUtils || (ViewUtils = {}));
