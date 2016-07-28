import datetime

from bokeh.embed import components
from bokeh.models import BoxAnnotation, Range1d, Span
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import Figure
import pytz

from vesper.util.bunch import Bunch
import vesper.ephem.ephem_utils as ephem_utils


_ONE_DAY = datetime.timedelta(days=1)


def create_rug_plot(station, night, times):
    
    solar_event_times = _get_solar_event_times(station, night)
    
    start, end = _get_rug_plot_x_axis_limits(solar_event_times, night)
    x_range = Range1d(start=start, end=end)
    
    y_range = Range1d(start=0, end=1)
    
    figure = Figure(
        x_range=x_range, y_range=y_range, height=50, sizing_mode='scale_width',
        toolbar_location=None)
    
    # Remove padding Bokeh puts around figure. Leave one pixel at the top
    # for the figure outline, which disappears if we set the `min_top_border`
    # attribute to zero.
    figure.min_border_left = 0
    figure.min_border_top = 1
    figure.min_border_right = 0
    figure.min_border_bottom = 0
    # figure.border_fill_color = 'red'
    
    figure.outline_line_color = 'black'
    
    # Configure X axis.
    figure.xaxis.major_tick_in = 0
    figure.xaxis.major_tick_out = 3
    figure.xaxis.formatter = DatetimeTickFormatter(
        formats=dict(
            hours=['%Hh'],
            days=['%Hh']))
    figure.xaxis.minor_tick_line_color = None
    
    # Hide Y axis and grid lines
    figure.yaxis.visible = False
    figure.xgrid.grid_line_color = None
    figure.ygrid.grid_line_color = None
    
    # Get time reference for timestamp computations.
    time_zone = pytz.timezone(station.time_zone)
    ref = time_zone.localize(datetime.datetime(1970, 1, 1))
 
    # Show sunrise/sunset information in background.
    if solar_event_times is not None:
        _add_solar_events_underlay(figure, solar_event_times, ref)
     
    # Get x coordinates of clip lines.
    xs = [_get_rug_plot_x(t, ref) for t in times]
 
    # Add clip lines.
    spans = \
        [Span(location=x, dimension='height', line_color='orange') for x in xs]
    figure.renderers.extend(spans)
    
    return components(figure)


def _get_solar_event_times(station, night):
    
    lat = station.latitude
    lon = station.longitude
    
    if lat is None or lon is None:
        return None
    
    else:
        # have station latitude and longitude
        
        time_zone = pytz.timezone(station.time_zone)
        
        times = Bunch()
        
        get = lambda e: _get_solar_event_time(e, lat, lon, night, time_zone)
        times.sunset = get('Sunset')
        times.civil_dusk = get('Civil Dusk')
        times.nautical_dusk = get('Nautical Dusk')
        times.astronomical_dusk = get('Astronomical Dusk')
        
        next_day = night + _ONE_DAY
        get = lambda e: _get_solar_event_time(e, lat, lon, next_day, time_zone)
        times.astronomical_dawn = get('Astronomical Dawn')
        times.nautical_dawn = get('Nautical Dawn')
        times.civil_dawn = get('Civil Dawn')
        times.sunrise = get('Sunrise')
        
        return times
    
    
def _get_solar_event_time(event, lat, lon, night, time_zone):
    dt = ephem_utils.get_event_time(event, lat, lon, night)
    return dt.astimezone(time_zone)


def _get_rug_plot_x_axis_limits(solar_event_times, night):

    # TODO: As far as I know, the four_hours adjustment in the following
    # should not be necessary. I did not use it with Boken 0.11.1 and
    # the plot was fine: I believe the problem only appeared with
    # Bokeh 0.12.0. Figure out what's wrong and fix it.
    if solar_event_times is not None:
        one_hour = datetime.timedelta(hours=1)
        four_hours = datetime.timedelta(hours=4)
        start = solar_event_times.sunset - one_hour - four_hours
        end = solar_event_times.sunrise + one_hour - four_hours
    
    else:
        midnight = datetime.datetime(night.year, night.month, night.day)
        start = midnight + datetime.timedelta(hours=17.5)
        end = midnight + datetime.timedelta(hours=31.5)
        
    return (start, end)


def _add_solar_events_underlay(figure, solar_event_times, ref):
    
    times = solar_event_times
    get = lambda e: _get_rug_plot_x(getattr(times, e), ref)
    
    sunset = get('sunset')
    civil_dusk = get('civil_dusk')
    nautical_dusk = get('nautical_dusk')
    astronomical_dusk = get('astronomical_dusk')
    
    astronomical_dawn = get('astronomical_dawn')
    nautical_dawn = get('nautical_dawn')
    civil_dawn = get('civil_dawn')
    sunrise = get('sunrise')
        
    civil_box = BoxAnnotation(
        plot=figure, left=sunset, right=sunrise, fill_alpha=1,
        fill_color='#999999')
    
    nautical_box = BoxAnnotation(
        plot=figure, left=civil_dusk, right=civil_dawn, fill_alpha=1,
        fill_color='#666666')
    
    astronomical_box = BoxAnnotation(
        plot=figure, left=nautical_dusk, right=nautical_dawn,
        fill_alpha=1, fill_color='#333333')
    
    night_box = BoxAnnotation(
        plot=figure, left=astronomical_dusk, right=astronomical_dawn,
        fill_alpha=1, fill_color='#000000')
    
    figure.renderers.extend(
        [civil_box, nautical_box, astronomical_box, night_box])


def _get_rug_plot_x(dt, ref):
    
    """
    Gets a timestamp suitable for plotting a vertical line in the
    clips rug plot for the specified time.
    
    The Bokeh plotting library that we use requires that the timestamp
    have units of milliseconds from midnight 1970-01-01.
    
    `dt` is the specified time, a `datetime` localized to the time zone
    of the clip's station.
    
    `ref` is local midnight 1970-01-01, localized to the time zone of
    the clip's station.
    """
    
    # We add `dt.dst()` to `dt - ref` to account for DST. During DST
    # this advances the returned timestamp by one hour.
    delta = dt - ref + dt.dst()
    return delta.total_seconds() * 1000


# def _get_rug_plot_xs(date, times):
#     
#     """
#     Gets the specified times in hours past midnight of the specified date.
#     
#     We assume that the times are in increasing order.
#     """
#     
#     if len(times) == 0:
#         return []
#     
#     else:
#         # have at least one time
#         
#         midnight = time_utils.create_utc_datetime(
#             date.year, date.month, date.day, time_zone=times[0].tzinfo)
# 
#         return [(t - midnight).total_seconds() / 3600 for t in times]
