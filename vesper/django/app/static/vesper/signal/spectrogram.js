import { Dft } from './dft.js';
export var Spectrogram;
(function (Spectrogram) {
    function allocateSpectrogramStorage(inputLength, params) {
        const p = params;
        const spectrumSize = p.dftSize / 2 + 1;
        const numSpectra = getNumSpectra(inputLength, p.window.length, p.hopSize);
        return new Float32Array(numSpectra * spectrumSize);
    }
    Spectrogram.allocateSpectrogramStorage = allocateSpectrogramStorage;
    function getNumSpectra(inputLength, recordSize, hopSize) {
        if (inputLength < recordSize)
            return 0;
        else
            return 1 + Math.floor((inputLength - recordSize) / hopSize);
    }
    Spectrogram.getNumSpectra = getNumSpectra;
    function computeSpectrogram(x, params, y) {
        const p = params;
        const window = p.window;
        const windowSize = window.length;
        const hopSize = p.hopSize;
        const dftSize = p.dftSize;
        const inputLength = x.length;
        const numSpectra = getNumSpectra(inputLength, windowSize, hopSize);
        const spectrumSize = dftSize / 2 + 1;
        const xx = new Float64Array(dftSize);
        const yy = new Float64Array(dftSize);
        let inputStart = 0;
        let inputEnd = inputStart + windowSize;
        let i = 0;
        let j = 0;
        let k = 0;
        const m = spectrumSize - 1;
        while (inputEnd <= inputLength) {
            j = inputStart;
            for (i = 0; i < windowSize; i++)
                xx[i] = x[j++] * window[i];
            Dft.computeRealForwardDft(xx, yy);
            y[k++] = yy[0] * yy[0];
            i = 1;
            j = dftSize - 1;
            while (i < m) {
                const re = yy[i++];
                const im = yy[j--];
                y[k++] = 2 * (re * re + im * im);
            }
            y[k++] = yy[m] * yy[m];
            inputStart += hopSize;
            inputEnd += hopSize;
        }
        if (p.referencePower !== null) {
            const outputLength = numSpectra * spectrumSize;
            computeDbValues(y, outputLength, p.referencePower);
        }
        return y;
    }
    Spectrogram.computeSpectrogram = computeSpectrogram;
    function computeDbValues(x, length, referencePower) {
        const minRatio = 1e-100;
        const minDbValue = 10 * Math.log10(minRatio);
        for (let i = 0; i < length; i++) {
            let r = x[i] / referencePower;
            if (r < minRatio)
                x[i] = minDbValue;
            else
                x[i] = 10 * Math.log10(r);
        }
    }
    Spectrogram.computeDbValues = computeDbValues;
})(Spectrogram || (Spectrogram = {}));
