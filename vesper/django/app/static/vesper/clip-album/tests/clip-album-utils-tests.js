import { DateTime, IANAZone }
    from '/static/third-party/luxon-2.2.0/luxon.min.js';

import { ClipAlbumUtils } from '/static/vesper/clip-album/clip-album-utils.js';


describe('ClipAlbumUtils', () => {


    const dateTime = DateTime.fromISO('2020-06-20T12:34:56.789Z');


    it('formatDateTime without options', () => {
        
        const cases = [
            ['US/Eastern', '2020-06-20 08:34:56.789'],
            ['US/Central', '2020-06-20 07:34:56.789'],
        ]

        for (const [timeZoneName, expected] of cases) {
            const timeZone = new IANAZone(timeZoneName);
            const actual = ClipAlbumUtils.formatDateTime(dateTime, timeZone);
            expect(actual).toBe(expected);
        }

    });


    it('formatDateTime with options', () => {

        // Options are:
        //     includeDate
        //     includeYear
        //     includeHourLeadingZero
        //     includeMillisecond

        const cases = [

            ['0000', '8:34:56'],
            ['0001', '8:34:56.789'],
            ['0010', '08:34:56'],
            ['0011', '08:34:56.789'],

            ['0100', '8:34:56'],
            ['0101', '8:34:56.789'],
            ['0110', '08:34:56'],
            ['0111', '08:34:56.789'],

            ['1000', '06-20 08:34:56'],
            ['1001', '06-20 08:34:56.789'],
            ['1010', '06-20 08:34:56'],
            ['1011', '06-20 08:34:56.789'],

            ['1100', '2020-06-20 08:34:56'],
            ['1101', '2020-06-20 08:34:56.789'],
            ['1110', '2020-06-20 08:34:56'],
            ['1111', '2020-06-20 08:34:56.789'],

        ];

        const timeZone = new IANAZone('US/Eastern');
        
        for (const [encodedOptions, expected] of cases) {

            const options = _getOptions(encodedOptions);

            const actual =
                ClipAlbumUtils.formatDateTime(dateTime, timeZone, options);

            expect(actual).toBe(expected);
            
        }


    });

});


function _getOptions(encodedOptions) {

    const chars = Array.from(encodedOptions);
    const bools = chars.map(c => c === '1');
    const [
        includeDate, includeYear, includeHourLeadingZero,
        includeMillisecond] = bools;

    return {
        includeDate: includeDate,
        includeYear: includeYear,
        includeHourLeadingZero: includeHourLeadingZero,
        includeMillisecond: includeMillisecond
    };

}
