export var TimeFrequencyUtils;
(function (TimeFrequencyUtils) {
    function timeToViewX(time, startTime, endTime, width) {
        return width * (time - startTime) / (endTime - startTime);
    }
    TimeFrequencyUtils.timeToViewX = timeToViewX;
    function getFreqRange(settings, halfSampleRate) {
        if (settings.frequencyRange !== undefined)
            return settings.frequencyRange;
        else
            return [0, 11025];
    }
    TimeFrequencyUtils.getFreqRange = getFreqRange;
    function freqToGramY(freq, halfSampleRate, numBins) {
        return numBins * (1. - freq / halfSampleRate);
    }
    TimeFrequencyUtils.freqToGramY = freqToGramY;
    function freqToViewY(freq, startFreq, endFreq, height) {
        return height * (1. - (freq - startFreq) / (endFreq - startFreq));
    }
    TimeFrequencyUtils.freqToViewY = freqToViewY;
})(TimeFrequencyUtils || (TimeFrequencyUtils = {}));
