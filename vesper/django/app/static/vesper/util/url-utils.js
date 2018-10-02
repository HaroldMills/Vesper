// I wrote this in JavaScript, following the style of array-utils.js,
// which was translated from TypeScript. We should eventually use
// TypeScript for this module, too.


export var UrlUtils;

(function (UrlUtils) {

    // Percent-encode a URL query parameter value. We encode the five
    // characters "!", "'", "(", ")", and "*" that are not encoded
    // by the `encodeURIComponent` function since they are reserved
    // by RFC 3986. Our code is derived from code that appears at
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/
    // Global_Objects/encodeURIComponent.
    function encodeQueryParameterValue(s) {
        return encodeURIComponent(s).replace(/[!'()*]/g, escape);
    }
    
    UrlUtils.encodeQueryParameterValue = encodeQueryParameterValue;
    
})(UrlUtils || (UrlUtils = {}));
