export var Dft;
(function (Dft) {
    function computeRealForwardDft(input, output) {
        const n = input.length;
        if (n == 1) {
            output[0] = input[0];
        }
        else {
            const x = output;
            const TWO_PI = 2 * Math.PI;
            const sqrt = Math.sqrt;
            let n2, n4, n8, nn, t1, t2, t3, t4, ix, id, i0, i1, i2, i3, i4, i5, i6, i7, i8, st1, cc1, ss1, cc3, ss3, e, a, rval, ival, mag;
            bitReverseArrayElements(input, output);
            for (ix = 0, id = 4; ix < n; id *= 4) {
                for (i0 = ix; i0 < n; i0 += id) {
                    st1 = x[i0] - x[i0 + 1];
                    x[i0] += x[i0 + 1];
                    x[i0 + 1] = st1;
                }
                ix = 2 * (id - 1);
            }
            n2 = 2;
            nn = n >>> 1;
            while ((nn = nn >>> 1)) {
                ix = 0;
                n2 = n2 << 1;
                id = n2 << 1;
                n4 = n2 >>> 2;
                n8 = n2 >>> 3;
                do {
                    if (n4 !== 1) {
                        for (i0 = ix; i0 < n; i0 += id) {
                            i1 = i0;
                            i2 = i1 + n4;
                            i3 = i2 + n4;
                            i4 = i3 + n4;
                            t1 = x[i3] + x[i4];
                            x[i4] -= x[i3];
                            x[i3] = x[i1] - t1;
                            x[i1] += t1;
                            i1 += n8;
                            i2 += n8;
                            i3 += n8;
                            i4 += n8;
                            t1 = x[i3] + x[i4];
                            t2 = x[i3] - x[i4];
                            t1 = -t1 * Math.SQRT1_2;
                            t2 *= Math.SQRT1_2;
                            st1 = x[i2];
                            x[i4] = t1 + st1;
                            x[i3] = t1 - st1;
                            x[i2] = x[i1] - t2;
                            x[i1] += t2;
                        }
                    }
                    else {
                        for (i0 = ix; i0 < n; i0 += id) {
                            i1 = i0;
                            i2 = i1 + n4;
                            i3 = i2 + n4;
                            i4 = i3 + n4;
                            t1 = x[i3] + x[i4];
                            x[i4] -= x[i3];
                            x[i3] = x[i1] - t1;
                            x[i1] += t1;
                        }
                    }
                    ix = (id << 1) - n2;
                    id = id << 2;
                } while (ix < n);
                e = TWO_PI / n2;
                for (let j = 1; j < n8; j++) {
                    a = j * e;
                    ss1 = Math.sin(a);
                    cc1 = Math.cos(a);
                    ss3 = 4 * ss1 * (0.75 - ss1 * ss1);
                    cc3 = 4 * cc1 * (cc1 * cc1 - 0.75);
                    ix = 0;
                    id = n2 << 1;
                    do {
                        for (i0 = ix; i0 < n; i0 += id) {
                            i1 = i0 + j;
                            i2 = i1 + n4;
                            i3 = i2 + n4;
                            i4 = i3 + n4;
                            i5 = i0 + n4 - j;
                            i6 = i5 + n4;
                            i7 = i6 + n4;
                            i8 = i7 + n4;
                            t2 = x[i7] * cc1 - x[i3] * ss1;
                            t1 = x[i7] * ss1 + x[i3] * cc1;
                            t4 = x[i8] * cc3 - x[i4] * ss3;
                            t3 = x[i8] * ss3 + x[i4] * cc3;
                            st1 = t2 - t4;
                            t2 += t4;
                            t4 = st1;
                            x[i8] = t2 + x[i6];
                            x[i3] = t2 - x[i6];
                            st1 = t3 - t1;
                            t1 += t3;
                            t3 = st1;
                            x[i4] = t3 + x[i2];
                            x[i7] = t3 - x[i2];
                            x[i6] = x[i1] - t1;
                            x[i1] += t1;
                            x[i2] = t4 + x[i5];
                            x[i5] -= t4;
                        }
                        ix = (id << 1) - n2;
                        id = id << 2;
                    } while (ix < n);
                }
            }
            var f = 1 / sqrt(n);
            for (let i = 0; i < n; i++)
                x[i] *= f;
        }
    }
    Dft.computeRealForwardDft = computeRealForwardDft;
    function bitReverseArrayElements(input, output) {
        const n = input.length;
        const n2 = n >>> 1;
        const nm1 = n - 1;
        output[0] = input[0];
        output[nm1] = input[nm1];
        if (n >= 4) {
            let i = 1, r = 0, h;
            do {
                r += n2;
                output[i] = input[r];
                output[r] = input[i];
                i++;
                h = n2 << 1;
                while (h = h >> 1, !((r ^= h) & h))
                    ;
                if (r >= i) {
                    output[i] = input[r];
                    output[r] = input[i];
                    output[nm1 - i] = input[nm1 - r];
                    output[nm1 - r] = input[nm1 - i];
                }
                i++;
            } while (i < n2);
        }
    }
    Dft.bitReverseArrayElements = bitReverseArrayElements;
})(Dft || (Dft = {}));
