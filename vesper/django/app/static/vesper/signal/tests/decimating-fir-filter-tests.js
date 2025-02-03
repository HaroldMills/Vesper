import { DecimatingFirFilter } from '../decimating-fir-filter.js';


function expectFilter(filter, coefficients, decimationFactor) {
    expect(filter.coefficients).toEqual(coefficients);
    expect(filter.decimationFactor).toEqual(decimationFactor);
}


function createTestFilter(coefficients, decimationFactor) {
    
    const coeffs = new Float64Array(coefficients);
    const filter = new DecimatingFirFilter(coeffs, decimationFactor);
    
    expect(filter.coefficients).toEqual(coeffs);
    expect(filter.decimationFactor).toEqual(decimationFactor);
    
    return filter;
    
}


function expectOutput(filter, inputs, outputs, inputFinal = false) {
    
    const inputArray = new Float32Array(inputs);
    
    let result = null;
    if (inputFinal)
        result = filter.process(inputArray, true);
    else
        result = filter.process(inputArray);
        
    const outputArray = new Float32Array(outputs);

    expect(result).toEqual(outputArray);
    
}


describe('DecimatingFirFilter', () => {


    it('constructor', () => {
        createTestFilter([1, -1, 1], 2);
    });


    it('process', () => {
        
        let filter = createTestFilter([1, -1, 1], 2);
        expectOutput(filter, [0, 1, 2, 3, 4, 5], [1, 2, 4]);
        expectOutput(filter, [6, 7, 8, 9, 10], [6, 8, -1], true);
        
        filter = createTestFilter([1, -1, 1, -1, 1], 3);
        expectOutput(filter, [0, 1, 2, 3, 4, 5], [1, 3]);
        expectOutput(filter, [6, 7, 8, 9, 10], [6, -2], true);
        
    });


});
