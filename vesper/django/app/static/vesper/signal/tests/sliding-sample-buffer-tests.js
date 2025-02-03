import { SlidingSampleBuffer } from '../sliding-sample-buffer.js';


function expectBuffer(b, startIndex, contents) {
    expect(b.startIndex).toBe(startIndex);
    expect(b.endIndex).toBe(startIndex + contents.length);
    expect(b.size).toBe(contents.length);
    expect(b.contents).toEqual(new Float32Array(contents));
}


describe('SlidingSampleBuffer', () => {


    it('constructor', () => {
        const buffer = new SlidingSampleBuffer(10);
        expect(buffer.capacity).toEqual(10);
    });
    
    
    it('append, appendZeros, and discard', () => {

        const b = new SlidingSampleBuffer(5);
        
        expect(b.capacity).toEqual(5);
        expectBuffer(b, 0, []);
        
        b.append([0, 1]);
        expectBuffer(b, 0, [0, 1]);
        
        b.append([2]);
        expectBuffer(b, 0, [0, 1, 2]);
        
        b.discard(2);
        expectBuffer(b, 2, [2]);
        
        b.append([]);
        expectBuffer(b, 2, [2]);
        
        b.append([3, 4, 5, 6]);
        expectBuffer(b, 2, [2, 3, 4, 5, 6]);
        
        b.discard(0);
        expectBuffer(b, 2, [2, 3, 4, 5, 6]);
        
        b.discard(3);
        expectBuffer(b, 5, [5, 6]);
        
        b.discard(2);
        expectBuffer(b, 7, []);
        
        b.appendZeros(2);
        expectBuffer(b, 7, [0, 0]);
        
        b.append([9]);
        expectBuffer(b, 7, [0, 0, 9]);
        
        b.discard(3);
        expectBuffer(b, 10, []);
        
    });
    
    
    it('exceptions', () => {
        const b = new SlidingSampleBuffer(1);
        expect(() => b.append([1, 2])).toThrow();
        expect(() => b.discard(1)).toThrow();
    });


});
