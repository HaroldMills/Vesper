import { SampleChunker } from '/static/vesper/signal/sample-chunker.js';


describe('SampleChunker', () => {


    it('constructor', () => {
        const chunker = new SampleChunker(3);
        expect(chunker.chunkSize).toEqual(3);
        expect(chunker.scaleFactor).toEqual(null);
    });
    
    
    it('chunk', () => {

        const cases = [
            [[3, 2], [[5, 1], [5, 2]]],
            [[3, 2], [[5, 1], [1, 1], [1, 0], [2, 1]]]
        ];
        
        for (const [[chunkSize, scaleFactor], writes] of cases) {
            
            const chunker = new SampleChunker(chunkSize, scaleFactor);
            expect(chunker.chunkSize).toEqual(chunkSize);
            expect(chunker.scaleFactor).toEqual(scaleFactor);
            
            let writeValue = 0;
            let readValue = 0;
            
            for (const [writeSize, chunkCount] of writes) {
                
                const samples = new Float32Array(writeSize);
                for (let i = 0; i < writeSize; i++)
                    samples[i] = writeValue++;
                    
                const chunks = chunker.chunk(samples);
                
                expect(chunks.length).toEqual(chunkCount);
                
                for (const chunk of chunks) {
                    
                    expect(chunk.length).toBe(chunkSize);
                    
                    for (const sample of chunk) {
                        expect(sample).toBe(readValue);
                        readValue += scaleFactor;
                    }

                }
                
            }
            
        }

    });


});
