export function timeToViewX(time, startTime, endTime, width) {
    return width * (time - startTime) / (endTime - startTime);
}


// TODO: Restore the default frequency range from [0, 11025] to
// [0, halfSampleRate] after clip album settings preset changes
// are applied properly.
function getFreqRange(settings, halfSampleRate) {
	if (settings.frequencyRange !== undefined)
		return settings.frequencyRange;
	else
		return [0, 11025];
}


// TODO: Look into the details of HTML canvas image rendering to
// determine the proper mapping between frequency and gram canvas
// coordinates. I think the simple mapping implemented here is probably
// not the best one, since it assumes that the gram canvas pixel height
// is halfSampleRate / numBins, i.e. (sampleRate / 2) / (dftSize / 2 + 1).
// That is incorrect: the gram canvas pixel height is the DFT bin size,
// sampleRate / dftSize. I suspect that the solution is to put zero hertz
// and half the sample rate in the middles of the bottom and top canvas
// pixels, respectively, rather than at the top and bottom of the canvas.
// The commented-out code below does this.
function freqToGramY(freq, halfSampleRate, numBins) {

    return numBins * (1. - freq / halfSampleRate);

//    const binSize = halfSampleRate / (numBins - 1)
//    return numBins - .5 - freq / binSize

}


function freqToViewY(freq, startFreq, endFreq, height) {
    return height * (1. - (freq - startFreq) / (endFreq - startFreq));
}


export const TimeFrequencyUtils = {
    'timeToViewX': timeToViewX,
    'getFreqRange': getFreqRange,
    'freqToGramY': freqToGramY,
    'freqToViewY': freqToViewY
};
