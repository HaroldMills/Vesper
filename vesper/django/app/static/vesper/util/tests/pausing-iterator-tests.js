import { Pauser } from '/static/vesper/util/pauser.js';
import { PausingIterator, PausingIteratorState }
    from '/static/vesper/util/pausing-iterator.js';


describe('PausingIterator', () => {


	it('constructor', () => {
		const i = new PausingIterator(null, 1, .5, 2, 1.25);
        expect(i.state).toBe(PausingIteratorState.Stopped);
        expect(i.startIndex).toBe(null);
        expect(i.endIndex).toBe(null);
        expect(i.pause).toBe(1);
        expect(i.minPause).toBe(.5);
        expect(i.maxPause).toBe(2);
        expect(i.pauseScaleFactor).toBe(1.25);
	});


    it('iterate synchronously', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const i = new PausingIterator(handler, .1, .05, .2, 1.25);
        await i.iterate(3, 5);
        expect(integers).toEqual([3, 4]);

    });


    it('iterate asynchronously', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const i = new PausingIterator(handler, .1, .05, .2, 1.25);
        i.iterate(3, 5);

        await Pauser.pause(.3);

        expect(integers).toEqual([3, 4]);

    });


    it('stop', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const i = new PausingIterator(handler, .1, .05, .2, 1.25);
        i.iterate(3, 5);

        await Pauser.pause(.05);

        i.stop();

        await Pauser.pause(.2);

        expect(integers).toEqual([3]);

    });


    it('stop cancels pause', async () => {

        const i = new PausingIterator(() => {}, 2, 1, 4, 1.25);

        const startTime = Date.now();

        setTimeout(() => i.stop(), .1 * 1000);

        await i.iterate(0, 2);

        const endTime = Date.now();
        const elapsedTime = endTime - startTime;
        expect(elapsedTime).toBeLessThan(.2 * 1000);

    })


    it('decreasePause', async () => {

        let times = [];

        function handler(i) {
            times.push(Date.now());
        }

        const i = new PausingIterator(handler, .125, .05, .3, 2);
        i.iterate(0, 3);

        await Pauser.pause(.05);

        i.decreasePause();
        expect(i.pause).toBe(.0625);

        await Pauser.pause(.2);

        expect(times.length).toBe(3);

        const elapsedTime = (times[2] - times[0]) / 1000;
        const diff = Math.abs(elapsedTime - .1875);
        expect(diff).toBeLessThan(.03);

    });


    it('increasePause', async () => {

        let times = [];

        function handler(i) {
            times.push(Date.now());
        }

        const i = new PausingIterator(handler, .125, .05, .3, 2);
        i.iterate(0, 3);

        await Pauser.pause(.05);

        i.increasePause();
        expect(i.pause).toBe(.25);

        await Pauser.pause(.5);

        expect(times.length).toBe(3);

        const elapsedTime = (times[2] - times[0]) / 1000;
        const diff = Math.abs(elapsedTime - .375);
        expect(diff).toBeLessThan(.03);

    });


    it('increasePause does nothing when not running', async () => {
        const i = new PausingIterator(() => {}, .125, .05, .2, 2);
        i.increasePause();
        await i.iterate(0, 2);
        i.increasePause();
        expect(i.pause).toBe(.125);
    });


    it('decreasePause does nothing when not running', async () => {
        const i = new PausingIterator(() => {}, .125, .05, .2, 2);
        i.decreasePause();
        await i.iterate(0, 2);
        i.decreasePause();
        expect(i.pause).toBe(.125);
    });


});
