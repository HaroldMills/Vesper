/*

Windows I'd like to offer:

Rectangular
Blackman [0.42, 0.50, 0.08]
Hamming [0.54, 0.46]
Hann [0.5, 0.5]
Nuttall [0.3635819, 0.4891775, 0.1365995, 0.0106411]
Gaussian
Kaiser
Slepian

*/


function createWindow(name, size) {

	if (name === "Rectangular")
		return createRectangularWindow(size);

	else if (name === "Hann")
		return createHannWindow(size);

	else
		throw `Unrecognized window type "${name}".`;

}


function createRectangularWindow(size) {
	const w = new Float64Array(size);
	for (let i = 0; i < size; i++)
		w[i] = 1;
	return w;
}


function createHannWindow(size) {
	const w = new Float64Array(size);
	const f = Math.PI / size;
	for (let i = 0; i < size; i++) {
		const sine = Math.sin(f * i);
		w[i] = sine * sine;
	}
	return w;
}


export const Window = {
    'createWindow': createWindow,
    'createRectangularWindow': createRectangularWindow,
    'createHannWindow': createHannWindow,
};
