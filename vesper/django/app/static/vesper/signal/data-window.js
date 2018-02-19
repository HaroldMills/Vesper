export var DataWindow;
(function (DataWindow) {
    function createWindow(name, size, symmetric = true) {
        if (name === 'Rectangular')
            return createRectangularWindow(size, symmetric);
        else if (name === 'Hann')
            return createHannWindow(size, symmetric);
        else
            throw `Unrecognized window type "${name}".`;
    }
    DataWindow.createWindow = createWindow;
    function createRectangularWindow(size, symmetric = true) {
        _checkWindowSize(size);
        const w = new Float64Array(size);
        for (let i = 0; i < size; i++)
            w[i] = 1;
        return w;
    }
    DataWindow.createRectangularWindow = createRectangularWindow;
    function _checkWindowSize(size) {
        if (size < 0)
            throw new Error('Window size must be nonnegative.');
        else if (Math.floor(size) !== size)
            throw new Error('Window size must be an integer.');
    }
    function createHannWindow(size, symmetric = true) {
        _checkWindowSize(size);
        const w = new Float64Array(size);
        if (size >= 2) {
            const f = Math.PI / (symmetric ? size - 1 : size);
            for (let i = 0; i < size; i++) {
                const sine = Math.sin(f * i);
                w[i] = sine * sine;
            }
        }
        return w;
    }
    DataWindow.createHannWindow = createHannWindow;
})(DataWindow || (DataWindow = {}));
