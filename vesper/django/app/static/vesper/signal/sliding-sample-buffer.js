export class SlidingSampleBuffer {
    
    
    constructor(capacity) {
        this._buffer = new Float32Array(capacity);
        this._bufferStartIndex = 0;
        this._contentsStartOffset = 0;
        this._contentsEndOffset = 0;
    }
    
    
    get capacity() {
        return this._buffer.length;
    }
    
    
    get startIndex() {
        return this._bufferStartIndex + this._contentsStartOffset;
    }
    
    
    get endIndex() {
        return this._bufferStartIndex + this._contentsEndOffset;
    }
    
    
    get size() {
        return this._contentsEndOffset - this._contentsStartOffset;
    }
    
    
    get contents() {
        return this._buffer.subarray(
            this._contentsStartOffset, this._contentsEndOffset);
    }
    
    
    appendZeros(count) {
        
        this._prepareForAppend(count);

        // Append zeros to buffer.
        let j = this._contentsEndOffset;
        for (let i = 0; i != count; i++)
            this._buffer[j++] = 0;
            
        // Update contents end offset.
        this._contentsEndOffset += count;

    }
    
    
    _prepareForAppend(appendSize) {
        
        // Check for buffer overflow.
        if (this.size + appendSize > this.capacity)
            throw new Error(`${this.constructor.name} overflow`);

        // Move contents to beginning of buffer if needed to make room
        // at end for new samples.
        if (this._contentsEndOffset + appendSize > this.capacity) {
            
            this._buffer.copyWithin(
                0, this._contentsStartOffset, this._contentsEndOffset);
                
            this._bufferStartIndex += this._contentsStartOffset;
            this._contentsEndOffset -= this._contentsStartOffset;
            this._contentsStartOffset = 0
            
        }

    }
    
    
    append(samples) {
        
        const count = samples.length;
        
        this._prepareForAppend(count);
        
        // Append samples to buffer.
        let j = this._contentsEndOffset;
        for (let i = 0; i != count; i++)
            this._buffer[j++] = samples[i];
            
        // Update contents end offset.
        this._contentsEndOffset += count;
        
    }
    
    
    discard(count) {
        
        if (count > this.size)
            throw new Error(`${this.constructor.name} underflow`);
            
        this._contentsStartOffset += count;
        
    }
    
    
}
