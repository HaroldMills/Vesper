export class TimeFrequencyUtils {


    static indexToTime(index, startIndex, sampleRate) {
        return (index - startIndex) / sampleRate;
    }


    static timeToViewX(time, startTime, endTime, width) {
        return width * (time - startTime) / (endTime - startTime);
    }


    static getViewFreqRange(settings, halfSampleRate) {
        if (settings.frequencyRange !== undefined)
            return settings.frequencyRange;
        else
            return [0, halfSampleRate];
    }


    static freqToGramY(freq, halfSampleRate, numBins) {
        return numBins * (1. - freq / halfSampleRate);
    }


    static freqToViewY(freq, startFreq, endFreq, height) {
        return height * (1. - (freq - startFreq) / (endFreq - startFreq));
    }


}
