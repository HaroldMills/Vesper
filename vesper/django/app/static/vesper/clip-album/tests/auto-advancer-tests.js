import { AutoAdvancer, AutoAdvancerState }
    from '/static/vesper/clip-album/auto-advancer.js';
import { Pauser } from '/static/vesper/util/pauser.js';


describe('AutoAdvancer', () => {


	it('constructor', () => {
		const a = new AutoAdvancer(null, 1, .5, 2, 1.25);
        expect(a.state).toBe(AutoAdvancerState.Stopped);
        expect(a.startIndex).toBe(null);
        expect(a.endIndex).toBe(null);
        expect(a.pause).toBe(1);
        expect(a.minPause).toBe(.5);
        expect(a.maxPause).toBe(2);
        expect(a.pauseScaleFactor).toBe(1.25);
	});


    it('iterate synchronously', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const a = new AutoAdvancer(handler, .1, .05, .2, 1.25);
        await a.start(3, 5);
        expect(integers).toEqual([3, 4]);

    });


    it('iterate asynchronously', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const a = new AutoAdvancer(handler, .1, .05, .2, 1.25);
        a.start(3, 5);

        await Pauser.pause(.3);

        expect(integers).toEqual([3, 4]);

    });


    it('stop', async () => {

        let integers = [];

        function handler(i) {
            integers.push(i);
        }

        const a = new AutoAdvancer(handler, .1, .05, .2, 1.25);
        a.start(3, 5);

        await Pauser.pause(.05);

        a.stop();

        await Pauser.pause(.2);

        expect(integers).toEqual([3]);

    });


    it('stop cancels pause', async () => {

        const a = new AutoAdvancer(() => {}, 2, 1, 4, 1.25);

        const startTime = Date.now();

        setTimeout(() => a.stop(), .1 * 1000);

        await a.start(0, 2);

        const endTime = Date.now();
        const elapsedTime = endTime - startTime;
        expect(elapsedTime).toBeLessThan(.2 * 1000);

    })


    it('decreasePause', async () => {

        let times = [];

        function handler(i) {
            times.push(Date.now());
        }

        const a = new AutoAdvancer(handler, .125, .05, .3, 2);
        a.start(0, 3);

        await Pauser.pause(.05);

        a.decreasePause();
        expect(a.pause).toBe(.0625);

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

        const a = new AutoAdvancer(handler, .125, .05, .3, 2);
        a.start(0, 3);

        await Pauser.pause(.05);

        a.increasePause();
        expect(a.pause).toBe(.25);

        await Pauser.pause(.5);

        expect(times.length).toBe(3);

        const elapsedTime = (times[2] - times[0]) / 1000;
        const diff = Math.abs(elapsedTime - .375);
        expect(diff).toBeLessThan(.03);

    });


    it('increasePause does nothing when not running', async () => {
        const a = new AutoAdvancer(() => {}, .125, .05, .2, 2);
        a.increasePause();
        await a.start(0, 2);
        a.increasePause();
        expect(a.pause).toBe(.125);
    });


    it('decreasePause does nothing when not running', async () => {
        const a = new AutoAdvancer(() => {}, .125, .05, .2, 2);
        a.decreasePause();
        await a.start(0, 2);
        a.decreasePause();
        expect(a.pause).toBe(.125);
    });


});
