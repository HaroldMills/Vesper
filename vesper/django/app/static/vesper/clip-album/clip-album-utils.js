export class ClipAlbumUtils {

    /**
     * Formats a Luxon `DateTime` in the specified time zone.
     * 
     * A `DateTime` formatted by this function with no `options` argument
     * looks like `2020-06-20 12:34:56.789`.
     * 
     * The `options` argument can be used to omit or alter some parts
     * of the result.
     * 
     * `options` fields (all default to `true` if omitted):
     * 
     *     includeDate
     *         `true` if date should be included.
     * 
     *         An example of a date is `2020-06-20`.
     * 
     *     includeYear
     *         `true` if year should be included in date.
     * 
     *          Ignored if `includeDate` is `false`.
     * 
     *          An example of a date without a year is `06-20`.
     * 
     *     includeHourLeadingZero
     *         `true` if hour should always have two digits, or `false`
     *         if the first digit of the two-digit hour should be omitted
     *         when it is zero.
     * 
     *         Ignored if `includeDate` is `true`.
     * 
     *     includeMillisecond
     *         `true` if time should include three millisecond digits.
     */
    static formatDateTime(dateTime, timeZone, options = {}) {

        const localDateTime = dateTime.setZone(timeZone);

        const isoString = localDateTime.toISO({includeOffset: false});

        let [date, time] = isoString.split('T');

        if (!_get(options.includeMillisecond))
            time = time.slice(0, -4);

        if (_get(options.includeDate)) {

            if (!_get(options.includeYear))
                date = date.slice(5);

            return `${date} ${time}`;

        } else {
            // date not included

            if (!_get(options.includeHourLeadingZero) && time.startsWith('0'))
                time = time.slice(1);

            return time;

        }

    }

}


function _get(option) {
    return option !== undefined ? option : true;
}
