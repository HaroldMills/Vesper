import { Pauser } from '/static/vesper/util/pauser.js';


describe('Pauser', () => {


	it('constructor', () => {
		const p = new Pauser(1);
        expect(p.duration).toBe(1);
	});


    it('pause', async () => {
        const requestedPause = .1;
        const p = new Pauser(requestedPause);
        const startTime = Date.now();
        await p.pause();
        const endTime = Date.now();
        const actualPause = (endTime - startTime) / 1000;
        expect(actualPause).toBeCloseTo(requestedPause, 2);
    });


    it('cancel', async () => {
        const requestedPause = 1;
        const cancelPause = .1;
        const p = new Pauser(requestedPause);
        setTimeout(() => p.cancel(), 1000 * cancelPause);
        const startTime = Date.now();
        await p.pause();
        const endTime = Date.now();
        const actualPause = (endTime - startTime) / 1000;
        expect(actualPause).toBeCloseTo(cancelPause, 2);
    });


    it('error if pause called more than once', () => {
        const p = new Pauser(.1);
        p.pause();
        expect(() => p.pause()).toThrowError();
    });


    it('error if cancel called before pause', () => {
        const p = new Pauser(.1);
        expect(() => p.cancel()).toThrowError();
    });


    it('no error if cancel called more than once', () => {
        const p = new Pauser(.1);
        p.pause();
        p.cancel();
        p.cancel();
        expect(true).toBe(true);
    });


});
