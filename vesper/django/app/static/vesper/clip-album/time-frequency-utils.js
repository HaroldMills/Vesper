export class TimeFrequencyUtils {


    static indexToTime(index, startIndex, sampleRate) {
        return (index - startIndex) / sampleRate;
    }


    static timeToViewX(time, startTime, endTime, viewWidth) {
        return viewWidth * (time - startTime) / (endTime - startTime);
    }


    static getViewFreqRange(settings, halfSampleRate) {
        if (settings.frequencyRange !== undefined)
            return settings.frequencyRange;
        else
            return [0, halfSampleRate];
    }


    static freqToGramY(freq, halfSampleRate, gramHeight) {

        // Since bins 0 and `gramHeight - 1` of a spectrogram are centered
        // at frequencies 0 and `halfSampleRate`, respectively, we map
        // frequency zero to the middle of the bottom gram canvas row
        // (taking into account that row indices increase from the top
        // of the canvas to the bottom), and half the sample rate to the
        // middle of the top gram row.
        const binSize = halfSampleRate / (gramHeight - 1);
        return gramHeight - (.5 + freq / binSize);

    }


    static freqToViewY(freq, startFreq, endFreq, viewHeight) {
        return viewHeight * (1. - (freq - startFreq) / (endFreq - startFreq));
    }


}
