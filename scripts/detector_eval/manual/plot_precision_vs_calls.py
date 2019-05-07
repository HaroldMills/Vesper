"""
Script that plots precision vs. number of calls for several detectors.

The plots are made for the archive of the current working directory
using the "Classification" and "Detector Score" annotations created
by the detectors.
"""


from pathlib import Path
import sqlite3

from bokeh.models import Range1d
from bokeh.models.tickers import SingleIntervalTicker
from bokeh.plotting import figure, output_file, show
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
import numpy as np


CREATE_MATPLOTLIB_PLOTS = True

CREATE_BOKEH_PLOTS = False

CREATE_SEPARATE_STATION_NIGHT_PLOTS = True

DATABASE_FILE_NAME = 'Archive Database.sqlite'

PLOTS_DIR_PATH = Path('/Users/harold/Desktop/Plots')

MATPLOTLIB_PLOT_FILE_NAME = 'Detector Precision vs. Calls.pdf'

BOKEH_PLOT_FILE_NAME_FORMAT = '{}_{}.html'

ALL_STATION_NIGHTS_PLOT_FILE_NAME = 'All Station-Nights.html'

DETECTOR_NAMES = [
    'MPG Ranch Tseep Detector 0.0 40',
    'MPG Ranch Thrush Detector 0.0 40',
    'BirdVoxDetect 0.1.a0 AT 02',
    'BirdVoxDetect 0.1.a0 AT 05'
]

PLOT_LINE_DATA = {
    
    'MPG Ranch Tseep 0.0': ('MPG Ranch Tseep Detector 0.0 40', 'blue'),
    'MPG Ranch Thrush 0.0': ('MPG Ranch Thrush Detector 0.0 40', 'green'),
    
    # Combination of MPG Ranch Tseep and Thrush detectors. It is a little
    # unfair to the detectors to sum their counts, since it effectively
    # forces them to share a threshold that would otherwise be chosen
    # independently for the different detectors to optimize their
    # performance, but the summation yields a precision-calls curve that
    # is more directly comparable to that of BirdVoxDetect.
    'MPG Ranch Combined 0.0': (
        ('MPG Ranch Tseep Detector 0.0 40',
         'MPG Ranch Thrush Detector 0.0 40'), 'red'),
    
    # This accommodates the fact that we used two different thresholds
    # when we ran BirdVoxDetect on a set of August, 2019 MPG Ranch
    # recordings. We ran the detector with a threshold of 2 on some
    # of the recordings, and with a threshold of 5 on the others. In
    # a case like this, in which exactly one of two detectors was run
    # on a given recording, summing counts from the two detectors for
    # a recording yields the counts of whichever detector was run on
    # that recording, since the counts for the detector that wasn't
    # run are all zero and contribute nothing to the sum.
    'BirdVoxDetect 0.1.a0 AT': (
        ('BirdVoxDetect 0.1.a0 AT 02',
         'BirdVoxDetect 0.1.a0 AT 05'), 'black'),
}

STATION_NIGHTS = '''
Angel / 2018-08-28
Bear / 2018-08-20
Bell Crossing / 2018-08-25
Bivory / 2018-08-20
CB Ranch / 2018-08-02
Coki / 2018-08-10
Cricket / 2018-08-31
Darby High School PC / 2018-08-09
Dashiell / 2018-08-17
Deer Mountain Lookout / 2018-08-30
DonnaRae / 2018-08-16
Dreamcatcher / 2018-08-19
Esmerelda / 2018-08-14
Evander / 2018-08-22
Florence High School / 2018-08-02
Grandpa's Pond / 2018-08-16
Heron Crossing / 2018-08-12
IBO Lucky Peak / 2018-08-17
IBO River / 2018-08-31
JJ / 2018-08-14
KBK / 2018-08-20
Kate / 2018-08-28
Lee Metcalf NWR / 2018-08-24
Lilo / 2018-08-30
Lost Trail / 2018-08-30
MPG North / 2018-08-07
MPG Ranch Floodplain SM2 / 2018-08-17
MPG Ranch Ridge / 2018-08-05
MPG Ranch Sheep Camp / 2018-08-10
MPG Ranch Subdivision / 2018-08-05
MPG Ranch Zumwalt Ridge / 2018-08-25
Max / 2018-08-17
Meadowlark / 2018-08-20
Mickey / 2018-08-26
Mitzi / 2018-08-09
Molly / 2018-08-30
Oxbow / 2018-08-18
Panda / 2018-08-30
Petey / 2018-08-26
Pocket Gopher / 2018-08-12
Sadie-Kate / 2018-08-20
Sasquatch / 2018-08-29
Seeley High School / 2018-08-05
Sleeman / 2018-08-23
Slocum / 2018-08-06
St Mary Lookout / 2018-08-18
Sula Peak Lookout / 2018-08-12
Sula Ranger Station / 2018-08-10
Teller / 2018-08-02
Walnut / 2018-08-24
Willow Mountain Lookout / 2018-08-16
YVAS / 2018-08-14
Zuri / 2018-08-03
'''

# STATION_NIGHTS = '''
# Angel / 2018-08-28
# Bear / 2018-08-20
# '''

NUM_SCORE_DECIMAL_PLACES = 4

QUERY_FORMAT = '''
select
    cast({} * round(score.value, {}) as integer) as Score,
    count(*) as Clips
from
    vesper_clip as clip
    inner join vesper_processor as processor
        on clip.creating_processor_id = processor.id
    inner join vesper_station as station
        on clip.station_id = station.id
    inner join vesper_string_annotation as score
        on clip.id = score.clip_id
    inner join vesper_annotation_info as score_info
        on score.info_id = score_info.id
    inner join vesper_string_annotation as classification
        on clip.id = classification.clip_id
    inner join vesper_annotation_info as classification_info
        on classification.info_id = classification_info.id
where
    processor.name = ? and
    station.name = ? and
    clip.date = ? and
    score_info.name = 'Detector Score' and
    classification_info.name = 'Classification' and
    classification.value {}
group by Score;
'''

CALL_CLIPS_QUERY = QUERY_FORMAT.format(
    10 ** NUM_SCORE_DECIMAL_PLACES, NUM_SCORE_DECIMAL_PLACES, "like 'Call%'")

NOISE_CLIPS_QUERY = QUERY_FORMAT.format(
    10 ** NUM_SCORE_DECIMAL_PLACES, NUM_SCORE_DECIMAL_PLACES, "= 'Noise'")


def main():
    
    print('Getting clip counts...')
    clip_counts = get_clip_counts()
    
    if CREATE_MATPLOTLIB_PLOTS:
        print('Creating Matplotlib plots...')
        create_matplotlib_plots(clip_counts)
        
    if CREATE_BOKEH_PLOTS:
        print('Creating Bokeh plots...')
        create_bokeh_plots(clip_counts)
        
    print('Done.')
        
        
def get_clip_counts():
    
    counts = {}
    
    for station_name, date in get_station_nights():
        counts[(station_name, date)] = get_station_night_clip_counts(
            station_name, date, DETECTOR_NAMES)
        
    return counts
        
        
def get_station_nights():
    return [s.split(' / ') for s in STATION_NIGHTS.strip().split('\n')]


def get_station_night_clip_counts(station_name, date, detector_names):
    
    clip_counts = {}
    
    for detector_name in detector_names:
        
        values = (detector_name, station_name, date)
        
        call_counts = get_cumulative_clip_counts(CALL_CLIPS_QUERY, values)
        noise_counts = get_cumulative_clip_counts(NOISE_CLIPS_QUERY, values)
 
        clip_counts[detector_name] = (call_counts, noise_counts)
            
    return clip_counts
    
    
def get_cumulative_clip_counts(query, values):
    
    db_file_path = Path.cwd() / DATABASE_FILE_NAME
    connection = sqlite3.connect(str(db_file_path))
    
    with connection:
        rows = connection.execute(query, values)
        
    counts = create_clip_counts_array()
    
    for score, count in rows:
        counts[score] = count
        
    connection.close()
              
    # Compute cumulative clip count sums so that element i of count
    # array is the number of clips whose scores are at least i.
    counts = np.flip(np.cumsum(np.flip(counts)))
    
    return counts
    
    
def create_clip_counts_array():
    length = 10 ** (NUM_SCORE_DECIMAL_PLACES + 2) + 1
    return np.zeros(length, dtype='int32')    
    
    
def create_matplotlib_plots(clip_counts):
    
    summed_clip_counts = sum_clip_counts(clip_counts)
    
    file_path = PLOTS_DIR_PATH / MATPLOTLIB_PLOT_FILE_NAME
    
    with PdfPages(file_path) as pdf:
        
        create_matplotlib_plot(
            pdf, 'All Station-Nights', PLOT_LINE_DATA, summed_clip_counts)
        
        if CREATE_SEPARATE_STATION_NIGHT_PLOTS:
        
            for station_name, date in get_station_nights():
                
                title = '{} / {}'.format(station_name, date)
                counts = clip_counts[(station_name, date)]
                create_matplotlib_plot(pdf, title, PLOT_LINE_DATA, counts)
                
 
def sum_clip_counts(clip_counts):
    
    summed_clip_counts = {}
    
    for station_night_clip_counts in clip_counts.values():
        
        for detector_name in DETECTOR_NAMES:
            
            try:
                call_counts, noise_counts = \
                    station_night_clip_counts[detector_name]
            except KeyError:
                continue
            
            try:
                summed_call_counts, summed_noise_counts = \
                    summed_clip_counts[detector_name]
            except KeyError:
                summed_call_counts, summed_noise_counts = \
                    (create_clip_counts_array(), create_clip_counts_array())
                
            summed_clip_counts[detector_name] = (
                summed_call_counts + call_counts,
                summed_noise_counts + noise_counts)
        
    return summed_clip_counts
        

def create_matplotlib_plot(pdf, title, line_data, clip_counts):
    
    plt.figure(figsize=(6, 6))
    
    axes = plt.gca()
    
    # Create plot lines.
    for line_name, (detector_names, line_color) in line_data.items():
        create_matplotlib_plot_line(
            axes, line_name, detector_names, line_color, clip_counts)

    # Set title and axis labels.
    plt.title(title)
    plt.xlabel('Calls')
    plt.ylabel('Precision (%)')
    
    # Set axis limits.
    plt.ylim((0, 100))
    
    # Configure grid.
    major_locator = MultipleLocator(20)
    minor_locator = MultipleLocator(5)
    axes.yaxis.set_major_locator(major_locator)
    axes.yaxis.set_minor_locator(minor_locator)
    plt.grid(which='both')
    plt.grid(which='minor', alpha=.4)
    
    # Show legend.
    axes.legend(prop={'size': 8})
    
    pdf.savefig()
    
    plt.close()
           

def create_matplotlib_plot_line(
        axes, line_name, detector_names, line_color, clip_counts):
    
    data = get_plot_data(detector_names, clip_counts)
    
    if data is not None:
        
        call_counts, precisions = data
        
        axes.plot(
            call_counts, precisions, color=line_color, label=line_name)
        
        
def get_plot_data(detector_names, clip_counts):
        
    try:
        call_counts, noise_counts = \
            get_plot_line_clip_counts(detector_names, clip_counts)
    except ValueError:
        return None
            
    total_counts = call_counts + noise_counts
        
    if total_counts[0] == 0:
        # no clips for this detector
        
        return None
    
    call_counts = reduce_size(call_counts)
    total_counts = reduce_size(total_counts)
    
    # Trim counts as needed to avoid divides by zero in precision
    # computations.
    indices = np.where(total_counts == 0)[0]
    if len(indices) != 0:
        end = indices[0]
        call_counts = call_counts[:end]
        total_counts = total_counts[:end]
        
    precisions = 100 * call_counts / total_counts.astype('float')

    # print('Precisions:', precisions)
    
    return call_counts, precisions
       

def get_plot_line_clip_counts(detector_names, clip_counts):
    
    if isinstance(detector_names, tuple):
        # `detector_names` is a tuple of string detector names
        
        # Get list of (call_counts, noise_counts) count array pairs.
        count_array_pairs = [
            get_plot_line_clip_counts_aux(n, clip_counts)
            for n in detector_names]
        
        # Separate call count and noise count arrays into separate tuples.
        call_count_arrays, noise_count_arrays = zip(*count_array_pairs)
        
        # Sum call count arrays and noise count arrays.
        call_counts = sum_arrays(call_count_arrays)
        noise_counts = sum_arrays(noise_count_arrays)
        
        return (call_counts, noise_counts)
    
    else:
        # `detector_names` is a single string detector name
        
        return get_plot_line_clip_counts_aux(detector_names, clip_counts)
    
    
def get_plot_line_clip_counts_aux(detector_name, clip_counts):
    
    try:
        return clip_counts[detector_name]
    
    except KeyError:
        raise ValueError(
            'Could not get clip counts for detector "{}".'.format(
                detector_name))
        
        
def sum_arrays(arrays):
    return np.stack(arrays).sum(axis=0)


def reduce_size(x):
    percent_size = 10 ** NUM_SCORE_DECIMAL_PLACES
    n = 99 * percent_size
    start = x[0:n:percent_size]
    end = x[n:]
    return np.concatenate((start, end))
    

def create_bokeh_plots(clip_counts):
        
    summed_clip_counts = sum_clip_counts(clip_counts)
    
    # Create plot for all station/nights.
    file_path = PLOTS_DIR_PATH / ALL_STATION_NIGHTS_PLOT_FILE_NAME
    create_bokeh_plot(
        file_path, 'All Station-Nights', PLOT_LINE_DATA, summed_clip_counts)
    
    if CREATE_SEPARATE_STATION_NIGHT_PLOTS:
        
        for station_name, date in get_station_nights():
            
            file_path = create_bokeh_plot_file_path(station_name, date)
            title = '{} / {}'.format(station_name, date)
            counts = clip_counts[(station_name, date)]
            create_bokeh_plot(file_path, title, PLOT_LINE_DATA, counts)
        

def create_bokeh_plot(file_path, title, line_data, clip_counts):

    output_file(file_path)
    
    tools = 'save'
    # tools = 'hover,save,pan,box_zoom,reset,wheel_zoom'
    
    p = figure(plot_width=700, plot_height=700, tools=tools)
    
    # Create plot lines.
    for line_name, (detector_names, line_color) in line_data.items():
        create_bokeh_plot_line(
            p, line_name, detector_names, line_color, clip_counts)
         
    p.title.text = title
    p.title.text_font_size = '12pt'
    
    p.axis.major_tick_line_color = None
    p.axis.minor_tick_line_color = None
    
    p.xaxis.axis_label = 'Calls'
    
    p.y_range = Range1d(0, 100)

    ticker = SingleIntervalTicker(interval=20, num_minor_ticks=4)
    
    p.yaxis.axis_label = 'Precision (%)'
    p.yaxis.ticker = ticker
    
    grid_line_color = 'black'
    grid_line_alpha = .3
    p.xgrid.grid_line_color = grid_line_color
    p.xgrid.grid_line_alpha = grid_line_alpha
    p.ygrid.ticker = ticker
    p.ygrid.grid_line_color = grid_line_color
    p.ygrid.grid_line_alpha = grid_line_alpha
    p.ygrid.minor_grid_line_color = grid_line_color
    p.ygrid.minor_grid_line_alpha = .1
    
    p.legend.location = 'top_right'
    p.legend.margin = 0
    p.legend.label_text_font_size = '8pt'
    
    show(p)
        

def create_bokeh_plot_line(
        p, line_name, detector_names, line_color, clip_counts):
    
    data = get_plot_data(detector_names, clip_counts)
    
    if data is not None:
        
        call_counts, precisions = data
        
        p.line(
            call_counts, precisions, legend=line_name,
            line_color=line_color, line_width=2)
          
              
def create_bokeh_plot_file_path(station_name, date):
    file_name = BOKEH_PLOT_FILE_NAME_FORMAT.format(station_name, date)
    return PLOTS_DIR_PATH / file_name


if __name__ == '__main__':
    main()
