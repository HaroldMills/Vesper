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

                for (let i = 0; i < inputSamples.length; ++i) {
                    
                    // TODO: Support optional playthrough.
                    outputSamples[i] = inputSamples[i] * 0;
                    
                    samples[i] = inputSamples[i];
                    
                }

                this.port.postMessage({ samples: samples });

                this._nextBufferNum =
                    (this._nextBufferNum + 1) % _RING_BUFFER_SIZE

                // if (this._nextBufferNum == 0)
                //     console.log('Ring buffer wrapped around.');

            }

        }

        return true;

    }

}


registerProcessor('ring-buffer-processor', RingBufferProcessor);
