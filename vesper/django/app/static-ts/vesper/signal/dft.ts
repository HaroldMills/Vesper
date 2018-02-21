/*
 * Function that computes the Discrete Fourier Transform (DFT) of a
 * real sequence.
 */


 export namespace Dft {


    /*
     * Computes the forward DFT of a real sequence.
     *
     * The DFT size n must be a power of two, and the input and output
     * arrays must have length n. On return, the output array contains the DFT
     * of the input array and the input array is unmodified. The real parts of
     * elements 0 through n / 2 of the DFT are stored in the corresponding
     * output array elements, and the imaginary parts of DFT elements 1
     * through n / 2 - 1 are stored in output array elements n - 1 through
     * n / 2 + 1, respectively (i.e. in reverse order from the end of the
     * array).
     *
     * Note that the output array does not include the imaginary
     * parts of DFT elements 0 and n / 2, since these are necessarily zero.
     * The output array also does not include DFT elements n / 2 + 1 through
     * n - 1, since these are the complex conjugates of the included elements
     * n / 2 - 1 through 1 (in reverse order), respectively.
     *
     * The code in this file has a long history. It is derived most
     * immediately from a portion of Corban Brook's dsp.js
     * (https://github.com/corbanbrook/dsp.js). The relevant portion of
     * dsp.js was in turn derived from code that is part of Jörg Arndt's FXT
     * library (see the file realfftsplitradix.cc of https://www.jjj.de/fxt,
     * and also pages 434-435 of Arndt's book Matters Computational, at
     * http://www.jjj.de/fxt/fxtbook.pdf). According to comments in Arndt's
     * code, it was derived from an original Fortran FFT (available at
     * https://www.jjj.de/fft/sorensen.tgz) that Sorensen et al. published
     * in the paper "Real-valued fast Fourier Transform Algorithms"
     * (IEEE Transactions on Acoustics, Speech, and Signal Processing,
     * Volume 35, Issue 6, June 1987, pp. 849-863), which was also
     * adapted to C by Bill Simpson in 1995 (see
     * https://www.jjj.de/fft/rsplitfft.c).
     */
    export function computeRealForwardDft(
        input: Float64Array, output: Float64Array
    ) {

        const n = input.length;

        if (n == 1) {

            output[0] = input[0];

        } else {
            // `n` is at least two, and the following code will work

            const x = output;
            const TWO_PI = 2 * Math.PI;
            const sqrt = Math.sqrt;
            let n2, n4, n8, nn,
                t1, t2, t3, t4,
                ix, id, i0, i1, i2, i3, i4, i5, i6, i7, i8,
                st1, cc1, ss1, cc3, ss3,
                e, a,
                rval, ival, mag;

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

                    } else {

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

                    // ss3 = sin(3 * a);
                    ss3 = 4 * ss1 * (0.75 - ss1 * ss1);

                    // cc3 = cos(3 * a);
                    cc3 = 4 * cc1 * (cc1 * cc1 - 0.75);

                    ix = 0; id = n2 << 1;

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

            // Scale output to make transform unitary.
            var f = 1 / sqrt(n);
            for (let i = 0; i < n; i++)
                x[i] *= f;

        }

    }


    /*
     * Permutes the elements of an array to bit-reversed index order.
     *
     * The input and output array lengths must have the same length `n`,
     * a power of two that is at least two.
     *
     * Element `i` of the input array is assigned to element `r(i)` of
     * the output array, where `r(i)` is `i` with its rightmost `log2(n)`
     * bits reversed.
     */
    export function bitReverseArrayElements(
        input: Float64Array, output: Float64Array
    ) {

        const n = input.length;
        const n2 = n >>> 1;
        const nm1 = n - 1;

        // Zero and `n - 1` are themselves bit-reversed. Note that these
        // lines correctly handle input lengths one and two, though the
        // second assignment is redundant for length two.
        output[0] = input[0];
        output[nm1] = input[nm1];

        if (n >= 4) {
            // `n` is at least four, so the following code will work

            let i = 1, r = 0, h;

            // Each iteration of this loop processes two values of `i`, the
            // first odd and the second even. When assignments are made to
            // elements of the output array, `r` is `i` with its rightmost
            // `log2(n)` bits reversed.
            do {

                // Increment `r` so its rightmost `log2(n)` bits are the
                // reverse of those of `i`. Here we know that bit `log2(n2)`
                // from the right of `r` is zero, so we can increment `r` by
                // just complementing that bit.
                r += n2;

                // At this point `i` is odd, so `r >= n2`. We do not need
                // to worry about performing redundant assignments here as
                // we do below since `i` will never attain the current value
                // of `r`, since this loop terminates when `i` reaches `n2`.
                // It also would not help to perform symmetric assignments
                // here as we do below since they would be redundant with
                // those we perform when `i` attains the value `nm1 - r`.
                output[i] = input[r];
                output[r] = input[i];

                i++;

                // Increment `r`. Following the rules of binary incrementation,
                // but processing bits from left to right rather than from
                // right to left, complement the bits of `r` from left to
                // right, starting at bit `log2(n2)` from the right and
                // proceeding through the first zero bit.
                h = n2 << 1;
                while (h = h >> 1, !((r ^= h) & h));

                // At this point `i` is even, so `r < n2`. We only perform
                // assignments if `r >= i` to avoid performing redundant
                // assignments in cases where `i` later attains the current
                // value of `r`. We also perform symmetric assignments to
                // elements of the second half of the output array.
                if (r >= i) {
                    output[i] = input[r];
                    output[r] = input[i];
                    output[nm1 - i] = input[nm1 - r];
                    output[nm1 - r] = input[nm1 - i];
                }

                i++;

            } while (i < n2)

        }

    }


    // The following is a version of the `bitReverseArrayElements` function
    // that I wrote as a clarification of the version above (that version
    // is from dsp.js). While I do believe the code of this function is
    // clearer (`i` and `r` are more in sync, for example, and the code
    // that increments `r` when bit `log2(n2)` from the right is one is
    // easier to understand), it is unfortunately also a little slower,
    // so I have left it commented out.
    //
    // I also tried precomputing a table of bit-reversed indices and
    // passing that to the `computeRealForwardDft` function so it would
    // not have to reperform the bit reversal computations on each
    // invocation, but that complicated the use of `computeRealForwardDft`
    // and (somewhat surprisingly) did not speed things up.
    /*
    export function bitReverseArrayElements(
        input: Float64Array, output: Float64Array
    ) {

        const n = input.length;
        const n2 = n / 2;
        const nm1 = n - 1;

        for (let i = 0, r = 0; i < n2; ) {

            // `r` is `i` with its rightmost `log2(n)` bits reversed.

            // At this point `i` is even, so `r < n2`. We only perform
            // assignments if `r >= i` to avoid performing redundant
            // assignments in cases where `i` later attains the current
            // value of `r`. We also perform symmetric assignments to
            // elements of the second half of the output array.
            if (r >= i) {
                output[i] = input[r];
                output[r] = input[i];
                output[nm1 - i] = input[nm1 - r];
                output[nm1 - r] = input[nm1 - i];
            }

            // Increment `i` and `r`. Here we know that bit `log2(n2)`
            // from the right of `r` is zero, so we can increment `r`
            // by just complementing that bit.
            i += 1;
            r |= n2;

            // At this point `i` is odd, so `r >= n2`. We do not need
            // to worry about performing redundant assignments here
            // since `i` will never attain the value of `r`. It also
            // would not help to perform the symmetric assignments
            // since they would be redundant with those we will perform
            // when `i` attains the value `nm1 - r`.

            // At this point `i` is odd, so `r >= n2`. We do not need
            // to worry about performing redundant assignments here as
            // we do above since `i` will never attain the current value
            // of `r`, since this loop terminates when `i` reaches `n2`.
            // It also would not help to perform symmetric assignments
            // here as we do above since they would be redundant with
            // those we perform when `i` attains the value `nm1 - r`.
            output[i] = input[r];
            output[r] = input[i];

            // Increment `i`.
            i += 1;


            // Increment r. Following the rules of binary incrementation,
            // but processing bits from left to right rather than from
            // right to left, complement the bits of `r` from left to
            // right, starting at bit `log2(n2)` from the right and
            // proceeding through the first zero bit.

            let bit = n2;

            // Complement leading ones. The loop always terminates since
            // the rightmost bit of `r` always starts as a zero, since
            // `i` is less than `n2`.
            while (r & bit) {
                r ^= bit;
                bit >>>= 1;
            }

            // Complement first zero.
            r |= bit;


        }

    }
    */


}
