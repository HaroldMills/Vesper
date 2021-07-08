// I wrote this in JavaScript, following the style of array-utils.js,
// which was translated from TypeScript. We might eventually want to
// use TypeScript for this module, too.


export var ClipAlbumUtils;

(function (ClipAlbumUtils) {
    
    /**
     Gets a rounded version of the time of day portion of the start time
     of a clip.
     
     The clip start time is a local date/time string as received from the
     server, for example "2020-10-02 02:06:44.537 EDT". We assume that
     the fractional part may be absent, and that when present it may
     have a variable number of digits.
     */
    function getRoundedClipStartTime(clip) {
        const timeOfDay = clip.startTime.split(' ')[1];
        const [hour, minute, second, fraction] = _parseTime(timeOfDay);
        return _roundTime(hour, minute, second, fraction);
    }
    
    
    function _parseTime(time) {
        
        // Split time into parts.
        const index = time.indexOf('.');
        const hhmmss = index === -1 ? time : time.slice(0, index);
        const [hh, mm, ss] = hhmmss.split(':');
        const f = index === -1 ? '0' : time.slice(index);
        
        // Parse parts.
        const hour = parseInt(hh);
        const minute = parseInt(mm);
        const second = parseInt(ss);
        const fraction = parseFloat(f);
        
        return [hour, minute, second, fraction];
        
    }
    
    
    function _roundTime(hour, minute, second, fraction) {
        
        if (fraction > .5 || fraction === .5 && second % 2 === 1) {
            
            // Round up to nearest second.
            
            second += 1;
            
            if (second === 60) {
                
                second = 0;
                minute += 1;
                
                if (minute === 60) {
                    
                    minute = 0;
                    hour += 1;
                    
                    if (hour === 24)
                        hour = 0
                        
                }
                
            }
            
        }
        
        const h = hour.toString();
        const mm = minute.toString().padStart(2, '0');
        const ss = second.toString().padStart(2, '0');
        
        return [h, mm, ss].join(':');
        
    }

    ClipAlbumUtils.getRoundedClipStartTime = getRoundedClipStartTime;
    
})(ClipAlbumUtils || (ClipAlbumUtils = {}));
