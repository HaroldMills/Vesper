class GainProcessor extends AudioWorkletProcessor {

  // Custom AudioParams can be defined with this static getter.
  static get parameterDescriptors() {
    return [{ name: 'gain', defaultValue: 1 }];
  }

  constructor() {
    // The super constructor call is required.
    super();
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    const gain = parameters.gain;
    for (let channel = 0; channel < input.length; ++channel) {
      const inputChannel = input[channel];
      console.log(`input channel length ${inputChannel.length}`);
      const outputChannel = output[channel];
      if (gain.length === 1) {
        for (let i = 0; i < inputChannel.length; ++i)
          // outputChannel[i] = inputChannel[i] * gain[0];
          outputChannel[i] = inputChannel[i] * 1;
      } else {
        for (let i = 0; i < inputChannel.length; ++i)
          // outputChannel[i] = inputChannel[i] * gain[i];
          outputChannel[i] = inputChannel[i] * 1;
      }
    }

    return true;
  }
}

registerProcessor('gain-processor', GainProcessor);
