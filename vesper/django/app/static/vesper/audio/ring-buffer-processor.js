const _INPUT_BUFFER_SIZE = 128;    // samples, Web Audio API render quantum
const _RING_BUFFER_SIZE = 1024;    // input buffers


class RingBufferProcessor extends AudioWorkletProcessor {


    constructor() {

        super();

        // Allocate sample buffers.
        this._buffers = [];
        for (let i = 0; i < _RING_BUFFER_SIZE; ++i)
            this._buffers.push(new Float32Array(_INPUT_BUFFER_SIZE));

        this._nextBufferNum = 0;
        
        this._bufferCount = 0;
        this._bufferStartIndex = 0;
        this._zeroRunLength = 0;

    }


    process(inputs, outputs, parameters) {

        const input = inputs[0];
        const output = outputs[0];

        for (let channelNum = 0; channelNum < input.length; ++channelNum) {

            // TODO: Support stereo recording.
            if (channelNum === 0) {

                const inputSamples = input[channelNum];
                const outputSamples = output[channelNum];
                const samples = this._buffers[this._nextBufferNum];

                // console.log(`input samples ${inputSamples.constructor.name}`);
                // console.log(
                //     `ring buffer input buffer length ${inputSamples.length}`);

                if (inputSamples.length !== _INPUT_BUFFER_SIZE) {
                    console.error(
                        `WARNING: Input buffer ${this._bufferCount} ` +
                        `contained ${inputSamples.length} samples ` +
                        `rather than the expected ${_INPUT_BUFFER_SIZE}.`);
                }
                
                for (let i = 0; i < inputSamples.length; ++i) {
                    
                    // TODO: Support optional playthrough.
                    outputSamples[i] = inputSamples[i] * 0;
                    
                    samples[i] = inputSamples[i];
                    
                    if (inputSamples[i] === 0) {
                        this._zeroRunLength += 1;
                    } else {
                        if (this._zeroRunLength >= 100) {
                            this.handleRunOfZeros(i);
                        }
                        this._zeroRunLength = 0;
                    }
                    
                }
                
                this.port.postMessage({ samples: samples });

                this._nextBufferNum =
                    (this._nextBufferNum + 1) % _RING_BUFFER_SIZE;
                    
                this._bufferCount += 1;
                this._bufferStartIndex += inputSamples.length;

                // if (this._nextBufferNum == 0)
                //     console.log('Ring buffer wrapped around.');

            }

        }

        return true;

    }
    

    handleRunOfZeros(i) {
        
        const startIndex = this._bufferStartIndex + i - this._zeroRunLength;
        
        console.error(
            `WARNING: Encountered ${this._zeroRunLength} zero samples ` +
            `starting at sample number ${startIndex}.`);
 
    }


}


registerProcessor('ring-buffer-processor', RingBufferProcessor);
