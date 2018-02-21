export var ArrayUtils;
(function (ArrayUtils) {
    function rangeArray(a, b = null, inc = 1) {
        if (inc == 0) {
            throw new Error('range increment must be nonzero');
        }
        let start;
        let end;
        if (b === null) {
            start = 0;
            end = a;
        }
        else {
            start = a;
            end = b;
        }
        const result = [];
        if (inc > 0) {
            for (let i = start; i < end; i += inc)
                result.push(i);
        }
        else {
            for (let i = start; i > end; i += inc)
                result.push(i);
        }
        return result;
    }
    ArrayUtils.rangeArray = rangeArray;
    function arraysEqual(a, b) {
        if (a.length !== b.length)
            return false;
        else {
            const n = a.length;
            for (let i = 0; i < n; i++)
                if (a[i] !== b[i])
                    return false;
            return true;
        }
    }
    ArrayUtils.arraysEqual = arraysEqual;
    function findLastLE(a, x) {
        if (x < a[0])
            return -1;
        else {
            let low = 0;
            let high = a.length;
            let mid;
            while (high != low + 1) {
                mid = Math.floor((low + high) / 2);
                if (a[mid] <= x)
                    low = mid;
                else
                    high = mid;
            }
            return low;
        }
    }
    ArrayUtils.findLastLE = findLastLE;
})(ArrayUtils || (ArrayUtils = {}));
