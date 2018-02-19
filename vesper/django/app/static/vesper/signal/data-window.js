export var DataWindow;
(function (DataWindow) {
    const _BLACKMAN_WEIGHTS = new Float64Array([0.42, -0.50, 0.08]);
    const _HAMMING_WEIGHTS = new Float64Array([.54, -.46]);
    const _HANN_WEIGHTS = new Float64Array([.5, -.5]);
    const _NUTTALL_WEIGHTS = new Float64Array([0.3635819, -0.4891775, 0.1365995, -0.0106411]);
    const _windowFunctions = new Map([
        ['Blackman', createBlackmanWindow],
        ['Hamming', createHammingWindow],
        ['Hann', createHannWindow],
        ['Nuttall', createNuttallWindow],
        ['Rectangular', createRectangularWindow]
    ]);
    function createBlackmanWindow(size, symmetric = true) {
        return createSumOfCosinesWindow(size, _BLACKMAN_WEIGHTS, symmetric);
    }
    DataWindow.createBlackmanWindow = createBlackmanWindow;
    function createSumOfCosinesWindow(size, weights, symmetric = true) {
        _checkWindowSize(size);
        const window = new Float64Array(size);
        if (size > 1) {
            const period = symmetric ? size - 1 : size;
            for (let i = 0; i < weights.length; i++) {
                const weight = weights[i];
                const phaseFactor = i * 2 * Math.PI / period;
                for (let j = 0; j < size; j++)
                    window[j] += weight * Math.cos(phaseFactor * j);
            }
        }
        else if (size === 1) {
            for (let i = 0; i < weights.length; i++)
                window[0] += weights[i];
        }
        return window;
    }
    DataWindow.createSumOfCosinesWindow = createSumOfCosinesWindow;
    function _checkWindowSize(size) {
        if (size < 0)
            throw new Error('Window size must be nonnegative.');
        else if (Math.floor(size) !== size)
            throw new Error('Window size must be an integer.');
    }
    function createRectangularWindow(size, symmetric = true) {
        _checkWindowSize(size);
        const window = new Float64Array(size);
        for (let i = 0; i < size; i++)
            window[i] = 1;
        return window;
    }
    DataWindow.createRectangularWindow = createRectangularWindow;
    function createHammingWindow(size, symmetric = true) {
        return createSumOfCosinesWindow(size, _HAMMING_WEIGHTS, symmetric);
    }
    DataWindow.createHammingWindow = createHammingWindow;
    function createHannWindow(size, symmetric = true) {
        return createSumOfCosinesWindow(size, _HANN_WEIGHTS, symmetric);
    }
    DataWindow.createHannWindow = createHannWindow;
    function createNuttallWindow(size, symmetric = true) {
        return createSumOfCosinesWindow(size, _NUTTALL_WEIGHTS, symmetric);
    }
    DataWindow.createNuttallWindow = createNuttallWindow;
    function createWindow(name, size, symmetric = true) {
        const windowFunction = _windowFunctions.get(name);
        if (windowFunction === undefined)
            throw `Unrecognized window type "${name}".`;
        else
            return windowFunction(size, symmetric);
    }
    DataWindow.createWindow = createWindow;
})(DataWindow || (DataWindow = {}));
