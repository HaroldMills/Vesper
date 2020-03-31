import { SlidingSampleBuffer }
    from '/static/vesper/signal/sliding-sample-buffer.js';


const _minBufferCapacity = 8192;


export class DecimatingFirFilter {
    
    
    constructor(coefficients, decimationFactor) {
        
        this._coefficients = new Float64Array(coefficients);
        this._decimationFactor = decimationFactor;
        
        const filterLength = coefficients.length;
        this._halfFilterLength = Math.floor((filterLength - 1) / 2);

        const capacity = Math.max(10 * filterLength, _minBufferCapacity);
        this._inputBuffer = new SlidingSampleBuffer(capacity);
        
        // Prime input buffer with `this._halfFilterLength` zeros so
        // first output sample is computed with filter centered over
        // first input sample.
        this._inputBuffer.appendZeros(this._halfFilterLength);
        
    }
    
    
    get coefficients() {
        return new Float64Array(this._coefficients);
    }
    
    
    get decimationFactor() {
        return this._decimationFactor;
    }
    
    
    process(samples, inputFinal = false) {
        
        // TODO: What is the best way to ensure that this won't overflow?
        this._inputBuffer.append(samples);
        
        if (inputFinal) {

            // Append `this._halfFilterLength` zeros to input buffer
            // so last output sample is computed with filter centered
            // over last input sample.
            this._inputBuffer.appendZeros(this._halfFilterLength);
            
        }
            
        const inputs = this._inputBuffer.contents;
        const filterLength = this._coefficients.length;
        const outputLength = this._getOutputLength(inputs.length);
        
        // TODO: Can we avoid allocating sample buffers during
        // signal processing?
        const outputs = new Float32Array(outputLength);
        
        let k = 0;
        
        for (let i = 0; i < outputLength; i++) {
        
            for (let j = 0; j < filterLength; j++)
                outputs[i] += this._coefficients[j] * inputs[k + j];
                
            k += this._decimationFactor;
                
        }
        
        this._inputBuffer.discard(outputLength * this._decimationFactor);
        
        return outputs;
        
    }
    
    
    _getOutputLength(inputLength) {
        
        const filterLength = this._coefficients.length;
        
        if (inputLength < filterLength) {
            // don't have enough input for any output
            
            return 0;
            
        } else {
            // have enough input for at least one output
            
            return 1 + Math.floor(
                (inputLength - filterLength) / this._decimationFactor);
                
        }
        
    }
    
    
}
