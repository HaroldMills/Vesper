import { UrlUtils } from '/static/vesper/util/url-utils.js';


describe('UrlUtils', () => {


    it('encodeQueryParameterValue', () => {

        const encode = UrlUtils.encodeQueryParameterValue;
        
        // Non-alphanumeric characters that should be escaped.
        const escapedChars = ' !"#$%&\'()+,/:;<=>?@[\\]^`{|}';
        for (let i = 0; i < escapedChars.length; i++) {
            const c = escapedChars[i];
            const result = encode(c);
            const expected = '%' + c.charCodeAt(0).toString(16).toUpperCase();
            expect(result).toEqual(expected);
        }
        
        // Non-alphanumeric characters that should not be escaped.
        const unescapedChars = '*-._~'
        for (let i = 0; i < unescapedChars.length; i++) {
            const c = unescapedChars[i];
            const result = encode(c);
            expect(result).toEqual(c);
        }
        
        
        // A few strings.
        
        const cases = [
            ['MPG Ranch Floodplain SM2+', 'MPG%20Ranch%20Floodplain%20SM2%2B'],
            ["Grandpa's Pond", 'Grandpa%27s%20Pond'],
            ["Wilson's Warbler", 'Wilson%27s%20Warbler']
        ];

        for (const [s, expected] of cases) {
            const result = encode(s);
            expect(result).toEqual(expected);
        }

    });


});
