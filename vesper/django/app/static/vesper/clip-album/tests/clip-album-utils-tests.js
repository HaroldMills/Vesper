import { ClipAlbumUtils } from '/static/vesper/clip-album/clip-album-utils.js';


describe('ClipAlbumUtils', () => {


    it('getRoundedClipStartTime', () => {
        
        const cases = [

            // round down
            ['2020-10-03 12:01:46.123 EDT', '12:01:46'],
            ['2020-10-03 12:01:46.12 EDT', '12:01:46'],
            ['2020-10-03 12:01:46.1 EDT', '12:01:46'],
            ['2020-10-03 12:01:46 EDT', '12:01:46'],
            
            // round up
            ['2020-10-03 12:01:46.789 EDT', '12:01:47'],
            ['2020-10-03 12:01:46.78 EDT', '12:01:47'],
            ['2020-10-03 12:01:46.7 EDT', '12:01:47'],
 
            // fraction of .5
            ['2020-10-03 12:01:45.5 EDT', '12:01:46'],
            ['2020-10-03 12:01:46.5 EDT', '12:01:46'],
            
            // single hour digit
            ['2020-10-03 02:01:46.123 EDT', '2:01:46'],
            
            // second wraparound
            ['2020-10-03 02:01:59.9 EDT', '2:02:00'],
            
            // minute wraparound
            ['2020-10-03 02:59:59.9 EDT', '3:00:00'],

            // hour wraparound
            ['2020-10-03 23:59:59.9 EDT', '0:00:00'],

        ];

        for (const [startTime, expected] of cases) {
            const clip = { startTime: startTime };
            const actual = ClipAlbumUtils.getRoundedClipStartTime(clip);
            expect(actual).toEqual(expected);
        }

    });


});
