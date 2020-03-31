/*

Sample chunker.

A `SampleChunker` partitions a stream of samples into fixed-size chunks.
The chunks are of type `Int16Array`. A `SampleChunker` optionally scales
the samples as it collects them.

A `SampleChunker` allocates each new chunk afresh, and relies on
JavaScript to garbage collect the allocated chunks when they are no
longer needed. A more storage-efficient approach would reuse chunks
from a fixed-size pool, but that would require chunk consumers to
explicitly free chunks when they were done with them.

*/


export class SampleChunker {
    
    
    constructor(chunkSize, scaleFactor = null) {
        
        this._chunkSize = chunkSize;
        this._scaleFactor = scaleFactor;
        
        this._chunk = new Int16Array(chunkSize);
        this._writeIndex = 0;
        
    }
    
    
    get chunkSize() {
        return this._chunkSize;
    }
    
    
    get scaleFactor() {
        return this._scaleFactor;
    }
    
    
    chunk(samples) {
        
        let sampleCount = samples.length;
        let readIndex = 0;
        const scaleFactor = this.scaleFactor;
        
        const chunks = [];
        let chunk = this._chunk;
        let writeIndex = this._writeIndex;
        
        while (sampleCount !== 0) {
            
            const freeSize = this.chunkSize - writeIndex;
            const copySize = Math.min(sampleCount, freeSize);
            
            if (this._scaleFactor !== null) {
                // scaling enabled
                
                for (let i = 0; i < copySize; i++)
                    chunk[writeIndex++] =
                        Math.round(scaleFactor * samples[readIndex++]);
                
            } else {
                // scaling disabled
                
                for (let i = 0; i < copySize; i++)
                    chunk[writeIndex++] = Math.round(samples[readIndex++]);
                        
            }
            
            sampleCount -= copySize;
            
            if (writeIndex === this.chunkSize) {
                // finished this chunk
                
                // Append chunk to chunks array.
                chunks.push(chunk);
                
                // Allocate a new chunk.
                chunk = new Int16Array(this.chunkSize);
                writeIndex = 0;
                
            }

        }
        
        // Save current chunk state.
        this._chunk = chunk;
        this._writeIndex = writeIndex;
        
        return chunks;
        
    }
    
    
}
