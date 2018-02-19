export var DataWindow;
(function (DataWindow) {
    function createWindow(name, size) {
        if (name === 'Rectangular')
            return createRectangularWindow(size);
        else if (name === 'Hann')
            return createHannWindow(size);
        else
            throw `Unrecognized window type "${name}".`;
    }
    DataWindow.createWindow = createWindow;
    function createRectangularWindow(size) {
        const w = new Float64Array(size);
        for (let i = 0; i < size; i++)
            w[i] = 1;
        return w;
    }
    DataWindow.createRectangularWindow = createRectangularWindow;
    function createHannWindow(size) {
        const w = new Float64Array(size);
        const f = Math.PI / size;
        for (let i = 0; i < size; i++) {
            const sine = Math.sin(f * i);
            w[i] = sine * sine;
        }
        return w;
    }
    DataWindow.createHannWindow = createHannWindow;
})(DataWindow || (DataWindow = {}));
