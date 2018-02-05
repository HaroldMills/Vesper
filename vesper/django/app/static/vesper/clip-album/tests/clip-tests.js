'use strict'


import { Clip } from '/static/vesper/clip-album/clip.js';


describe('Clip', () => {


	it('construction and properties', () => {

		const num = 23;
		const id = 24;
		const length = 1000;
		const sampleRate = 22050.;
		const startTime = "2017-05-18 10:19:00 EDT";
		const clip = new Clip(num, id, length, sampleRate, startTime);

		expect(clip.num).toBe(num);
		expect(clip.id).toBe(id);
		expect(clip.length).toBe(length);
		expect(clip.sampleRate).toBe(sampleRate);
		expect(clip.startTime).toBe(startTime);

		expect(clip.url).toBe('/clips/24/');
		expect(clip.wavFileUrl).toBe('/clips/24/wav/');
		expect(clip.annotationsUrl).toBe('/clips/24/annotations/');
		expect(clip.annotationsJsonUrl).toBe('/clips/24/annotations/json/');
		expect(clip.getAnnotationUrl('bobo')).toBe(
			'/clips/24/annotations/bobo/');

		expect(clip.samples).toBe(null);
		clip.samples = [];
		expect(clip.samples.length).toBe(0);

		expect(clip.annotations).toBe(null);
		clip.annotations = new Map();
		expect(clip.annotations.size).toBe(0);
		clip.annotations.set('Classification', 'Call');
		expect(clip.annotations.size).toBe(1);
		expect(clip.annotations.get('Classification')).toBe('Call');
		clip.annotations = new Map([['one', 1], ['two', 2]]);
		expect(clip.annotations.size).toBe(2);
		expect(clip.annotations.get('one')).toBe(1);

	});


});
