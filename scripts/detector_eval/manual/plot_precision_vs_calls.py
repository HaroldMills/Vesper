"""
Script that plots precision vs. number of calls for several detectors.

The plots are made for the archive of the current working directory
using the "Classification" and "Detector Score" annotations created
by the detectors.
"""


from pathlib import Path
import itertools
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

CREATE_SEPARATE_STATION_NIGHT_PLOTS = False

DATABASE_FILE_NAME = 'Archive Database.sqlite'

# PLOTS_DIR_PATH = Path(
#     '/Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Detector Comparison/'
#     '0.0/Plots')
PLOTS_DIR_PATH = Path('/Users/harold/Desktop/Plots')

MATPLOTLIB_PLOT_FILE_NAME = 'Detector Precision vs. Calls.pdf'

BOKEH_PLOT_FILE_NAME_FORMAT = '{}_{}.html'

ALL_STATION_NIGHTS_PLOT_FILE_NAME = 'All Station-Nights.html'

# DETECTOR_NAMES = [
#     'MPG Ranch Tseep Detector 0.0 40',
#     'MPG Ranch Thrush Detector 0.0 40',
#     'BirdVoxDetect 0.1.a0 AT 02',
#     'BirdVoxDetect 0.1.a0 AT 05'
# ]
DETECTOR_NAMES = [
    'MPG Ranch Thrush Detector 1.0 40',
    'MPG Ranch Tseep Detector 1.0 20',
]

PLOT_LINE_DATA = {
    
    # 'MPG Ranch Tseep 0.0': ('MPG Ranch Tseep Detector 0.0 40', 'blue'),
    # 'MPG Ranch Thrush 0.0': ('MPG Ranch Thrush Detector 0.0 40', 'green'),
    'MPG Ranch Thrush 1.0': ('MPG Ranch Thrush Detector 1.0 40', 'green'),
    'MPG Ranch Tseep 1.0': ('MPG Ranch Tseep Detector 1.0 20', 'blue'),
    
    # Combination of MPG Ranch Tseep and Thrush detectors. It is a little
    # unfair to the detectors to sum their counts, since it effectively
    # forces them to share a threshold that would otherwise be chosen
    # independently for the different detectors to optimize their
    # performance, but the summation yields a precision-calls curve that
    # is more directly comparable to that of BirdVoxDetect.
#     'MPG Ranch Combined 0.0': (
#         ('MPG Ranch Tseep Detector 0.0 40',
#          'MPG Ranch Thrush Detector 0.0 40'), 'red'),
    
    # This accommodates the fact that we used two different thresholds
    # when we ran BirdVoxDetect on a set of August, 2019 MPG Ranch
    # recordings. We ran the detector with a threshold of 2 on some
    # of the recordings, and with a threshold of 5 on the others. In
    # a case like this, in which exactly one of two detectors was run
    # on a given recording, summing counts from the two detectors for
    # a recording yields the counts of whichever detector was run on
    # that recording, since the counts for the detector that wasn't
    # run are all zero and contribute nothing to the sum.
#     'BirdVoxDetect 0.1.a0 AT': (
#         ('BirdVoxDetect 0.1.a0 AT 02',
#          'BirdVoxDetect 0.1.a0 AT 05'), 'black'),

}

OLD_BIRD_DETECTOR_NAMES = [
    'Old Bird Thrush Detector Redux 1.1',
    'Old Bird Tseep Detector Redux 1.1',
]

OLD_BIRD_PLOT_DATA = {
    'Old Bird Thrush Redux 1.1':
        ('Old Bird Thrush Detector Redux 1.1', 'green'),
    'Old Bird Tseep Redux 1.1':
       ('Old Bird Tseep Detector Redux 1.1', 'blue'),
}

ARCHIVE_NAMES = ['Part 1', 'Part 2']

ARCHIVE_INFOS = {
    
    'Part 1': (
        
        Path(
            '/Users/harold/Desktop/NFC/Data/MPG Ranch/'
            '2019-07 Detector Development/Evaluation Archives/2018 Part 1'),
        
        # Station-nights for 2018 MPG Ranch August archive, from output of
        # `scripts.detector_eval.manual.prune_recordings` script.
        '''
        Angel / 2018-08-17
        Bear / 2018-08-09
        Bell Crossing / 2018-08-01
        Bivory / 2018-08-31
        CB Ranch / 2018-08-18
        Coki / 2018-08-12
        Cricket / 2018-08-14
        Darby High School PC / 2018-08-28
        Dashiell / 2018-08-23
        Deer Mountain Lookout / 2018-08-10
        DonnaRae / 2018-08-04
        Dreamcatcher / 2018-08-29
        Esmerelda / 2018-08-28
        Evander / 2018-08-25
        Florence High School / 2018-08-17
        Grandpa's Pond / 2018-08-30
        Heron Crossing / 2018-08-15
        IBO Lucky Peak / 2018-08-27
        IBO River / 2018-08-23
        JJ / 2018-08-11
        KBK / 2018-08-10
        Kate / 2018-08-18
        Lee Metcalf NWR / 2018-08-19
        Lilo / 2018-08-13
        Lost Trail / 2018-08-05
        MPG North / 2018-08-11
        MPG Ranch Floodplain SM2 / 2018-08-20
        MPG Ranch Ridge / 2018-08-23
        MPG Ranch Sheep Camp / 2018-08-29
        MPG Ranch Subdivision / 2018-08-18
        MPG Ranch Zumwalt Ridge / 2018-08-20
        Max / 2018-08-26
        Meadowlark / 2018-08-08
        Mickey / 2018-08-09
        Mitzi / 2018-08-02
        Molly / 2018-08-22
        Oxbow / 2018-08-07
        Panda / 2018-08-24
        Petey / 2018-08-20
        Pocket Gopher / 2018-08-16
        Sadie-Kate / 2018-08-11
        Sasquatch / 2018-08-19
        Seeley High School / 2018-08-20
        Sleeman / 2018-08-08
        Slocum / 2018-08-24
        St Mary Lookout / 2018-08-15
        Sula Peak Lookout / 2018-08-31
        Sula Ranger Station / 2018-08-31
        Teller / 2018-08-13
        Walnut / 2018-08-07
        Willow Mountain Lookout / 2018-08-17
        YVAS / 2018-08-02
        Zuri / 2018-08-13
        '''
    ),
    
    'Part 2': (
        
        Path(
            '/Users/harold/Desktop/NFC/Data/MPG Ranch/'
            '2019-07 Detector Development/Evaluation Archives/2018 Part 2'),
        
        # Station-nights for 2018 MPG Ranch September archive, from output of
        # `scripts.detector_eval.manual.prune_recordings` script.
        '''
        Angel / 2018-09-30
        Bear / 2018-09-09
        Bell Crossing / 2018-09-20
        Bivory / 2018-09-05
        CB Ranch / 2018-09-23
        Coki / 2018-09-19
        Cricket / 2018-09-12
        Darby High School PC / 2018-09-11
        Dashiell / 2018-09-11
        Deer Mountain Lookout / 2018-09-16
        DonnaRae / 2018-09-23
        Dreamcatcher / 2018-09-25
        Esmerelda / 2018-09-08
        Evander / 2018-09-07
        Florence High School / 2018-09-20
        Grandpa's Pond / 2018-09-08
        Heron Crossing / 2018-09-04
        IBO Lucky Peak / 2018-09-13
        IBO River / 2018-09-09
        JJ / 2018-09-04
        KBK / 2018-09-11
        Kate / 2018-09-25
        Lee Metcalf NWR / 2018-09-02
        Lilo / 2018-09-12
        Lost Trail / 2018-09-03
        MPG North / 2018-09-12
        MPG Ranch Floodplain / 2018-09-30
        MPG Ranch Ridge / 2018-09-10
        MPG Ranch Sheep Camp / 2018-09-14
        MPG Ranch Subdivision / 2018-09-02
        Max / 2018-09-20
        Meadowlark / 2018-09-26
        Mickey / 2018-09-14
        Mitzi / 2018-09-06
        Molly / 2018-09-24
        Oxbow / 2018-09-09
        Panda / 2018-09-08
        Petey / 2018-09-12
        Pocket Gopher / 2018-09-20
        Sasquatch / 2018-09-30
        Seeley High School / 2018-09-14
        Sleeman / 2018-09-13
        Slocum / 2018-09-10
        St Mary Lookout / 2018-09-05
        Sula Peak Lookout / 2018-09-03
        Sula Ranger Station / 2018-09-14
        Teller / 2018-09-07
        Walnut / 2018-09-01
        Willow Mountain Lookout / 2018-09-01
        YVAS / 2018-09-18
        Zuri / 2018-09-20
        '''

    )
}

NUM_SCORE_DECIMAL_PLACES = 2

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

# TODO: For each plot line, automatically plot to the lowest score for
# which relevant clips were not pruned from the archive database. Note
# that that score may vary with the plot line (detector(s) and
# station-night). I believe it is safe to use for each combination of
# detector, station, and night the lowest score that a clip for that
# combination has in the archive database, and that that score can be
# determined from the clip counts that we retrieve from the database.

MIN_PLOT_LINE_SCORES = {
    
    'MPG Ranch Thrush 1.0': 40,
    'MPG Ranch Tseep 1.0': 20,
    
    # 46 for Part 1, 30 for Part 2, 46 for both
    'BirdVoxDetect 0.1.a0 AT': 46
    
}

DEFAULT_MIN_PLOT_LINE_SCORE = 80

OLD_BIRD_QUERY_FORMAT = '''
select
    count(*) as Clips
from
    vesper_clip as clip
    inner join vesper_processor as processor
        on clip.creating_processor_id = processor.id
    inner join vesper_station as station
        on clip.station_id = station.id
    inner join vesper_string_annotation as classification
        on clip.id = classification.clip_id
    inner join vesper_annotation_info as classification_info
        on classification.info_id = classification_info.id
where
    processor.name = ? and
    station.name = ? and
    clip.date = ? and
    classification_info.name = 'Classification' and
    classification.value {};
'''

OLD_BIRD_CALL_CLIPS_QUERY = OLD_BIRD_QUERY_FORMAT.format("like 'Call%'")

OLD_BIRD_NOISE_CLIPS_QUERY = OLD_BIRD_QUERY_FORMAT.format("= 'Noise'")


def main():
    
    print('Getting clip counts...')
    clip_counts = get_clip_counts()
    old_bird_clip_counts = get_old_bird_clip_counts()
    
    if CREATE_MATPLOTLIB_PLOTS:
        print('Creating Matplotlib plots...')
        create_matplotlib_plots(clip_counts, old_bird_clip_counts)
        
    if CREATE_BOKEH_PLOTS:
        print('Creating Bokeh plots...')
        create_bokeh_plots(clip_counts, old_bird_clip_counts)
        
    print('Done.')
        
        
def get_clip_counts():
    dicts = [get_archive_clip_counts(name) for name in ARCHIVE_NAMES]
    return dict(itertools.chain.from_iterable(d.items() for d in dicts))


def get_archive_clip_counts(archive_name):
    
    archive_dir_path, station_nights = ARCHIVE_INFOS[archive_name]
    station_nights = parse_station_nights(station_nights)
    
    return dict(
        (station_night,
         get_station_night_clip_counts(archive_dir_path, *station_night))
        for station_night in station_nights)
        
        
def parse_station_nights(station_nights):
    return [
        tuple(s.strip().split(' / '))
        for s in station_nights.strip().split('\n')]


def get_station_night_clip_counts(archive_dir_path, station_name, date):
    get_counts = get_station_night_clip_counts_aux
    return dict(
        (detector_name,
         get_counts(archive_dir_path, detector_name, station_name, date))
        for detector_name in DETECTOR_NAMES)
    
    
def get_station_night_clip_counts_aux(
        archive_dir_path, detector_name, station_name, date):
    
    values = (detector_name, station_name, date)
    call_counts = get_cumulative_clip_counts(
        archive_dir_path, CALL_CLIPS_QUERY, values)
    noise_counts = get_cumulative_clip_counts(
        archive_dir_path, NOISE_CLIPS_QUERY, values)
    return call_counts, noise_counts


def get_cumulative_clip_counts(archive_dir_path, query, values):
    
    db_file_path = archive_dir_path / DATABASE_FILE_NAME
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
    
    
def get_old_bird_clip_counts():
    dicts = [get_archive_old_bird_clip_counts(name) for name in ARCHIVE_NAMES]
    return dict(itertools.chain.from_iterable(d.items() for d in dicts))


def get_archive_old_bird_clip_counts(archive_name):
    
    archive_dir_path, station_nights = ARCHIVE_INFOS[archive_name]
    station_nights = parse_station_nights(station_nights)
    get_counts = get_old_bird_station_night_clip_counts
    
    return dict(
        (station_night, get_counts(archive_dir_path, *station_night))
        for station_night in station_nights)
        
        
def get_old_bird_station_night_clip_counts(
        archive_dir_path, station_name, date):
    
    get_counts = get_old_bird_station_night_clip_counts_aux
    
    return dict(
        (detector_name,
         get_counts(archive_dir_path, detector_name, station_name, date))
        for detector_name in OLD_BIRD_DETECTOR_NAMES)
    
    
def get_old_bird_station_night_clip_counts_aux(
        archive_dir_path, detector_name, station_name, date):
    
    get_count = get_old_bird_clip_count
    
    values = (detector_name, station_name, date)

    call_count = get_count(archive_dir_path, OLD_BIRD_CALL_CLIPS_QUERY, values)
    noise_count = \
        get_count(archive_dir_path, OLD_BIRD_NOISE_CLIPS_QUERY, values)
        
    return call_count, noise_count


def get_old_bird_clip_count(archive_dir_path, query, values):

    db_file_path = archive_dir_path / DATABASE_FILE_NAME
    connection = sqlite3.connect(str(db_file_path))
    
    with connection:
        rows = connection.execute(query, values)
        
    count = list(rows)[0][0]
        
    connection.close()
              
    return count


def create_matplotlib_plots(clip_counts, old_bird_clip_counts):
    
    summed_clip_counts = sum_clip_counts(clip_counts)
    summed_old_bird_clip_counts = \
        sum_old_bird_clip_counts(old_bird_clip_counts)
    
    file_path = PLOTS_DIR_PATH / MATPLOTLIB_PLOT_FILE_NAME
    
    with PdfPages(file_path) as pdf:
        
        create_matplotlib_plot(
            pdf, 'All Station-Nights', summed_clip_counts,
            summed_old_bird_clip_counts)
        
        if CREATE_SEPARATE_STATION_NIGHT_PLOTS:
        
            station_nights = sorted(clip_counts.keys())
            
            for station_night in station_nights:
                
                title = '{} / {}'.format(*station_night)
                counts = clip_counts[station_night]
                old_bird_counts = old_bird_clip_counts[station_night]
                create_matplotlib_plot(pdf, title, counts, old_bird_counts)
                
 
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
                summed_call_counts, summed_noise_counts = (
                    create_clip_counts_array(), create_clip_counts_array())
                
            summed_clip_counts[detector_name] = (
                summed_call_counts + call_counts,
                summed_noise_counts + noise_counts)
                
    return summed_clip_counts
        

def sum_old_bird_clip_counts(clip_counts):
    
    sum_clip_counts = sum_old_bird_clip_counts_aux
    
    return dict(
        (detector_name, sum_clip_counts(detector_name, clip_counts))
        for detector_name in OLD_BIRD_DETECTOR_NAMES)
    
    
def sum_old_bird_clip_counts_aux(detector_name, clip_counts):
    count_pairs = [v[detector_name] for v in clip_counts.values()]
    call_counts, noise_counts = tuple(zip(*count_pairs))
    return sum_counts(call_counts), sum_counts(noise_counts)


def sum_counts(counts):
    return np.array(counts).sum()


def create_matplotlib_plot(pdf, title, clip_counts, old_bird_clip_counts):
    
    plt.figure(figsize=(6, 6))
    
    axes = plt.gca()
    
    # Create plot lines.
    for line_name, (detector_names, line_color) in PLOT_LINE_DATA.items():
        create_matplotlib_plot_line(
            axes, line_name, detector_names, line_color, clip_counts)
        
    # Create Old Bird markers.
    for marker_name, (detector_name, marker_color) in \
            OLD_BIRD_PLOT_DATA.items():
        
        create_matplotlib_plot_marker(
            axes, marker_name, detector_name, marker_color,
            old_bird_clip_counts)

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
    # axes.legend(prop={'size': 8}, loc=(.04, .13))

    pdf.savefig()
    
    plt.close()
           

def create_matplotlib_plot_line(
        axes, line_name, detector_names, line_color, clip_counts):
    
    data = get_plot_line_data(line_name, detector_names, clip_counts)
    
    if data is not None:
        call_counts, precisions = data
        axes.plot(call_counts, precisions, color=line_color, label=line_name)
        
        
def get_plot_line_data(line_name, detector_names, clip_counts):
        
    try:
        call_counts, noise_counts = \
            get_plot_line_clip_counts(detector_names, clip_counts)
    except ValueError:
        return None
            
    total_counts = call_counts + noise_counts
        
    if total_counts[0] == 0:
        # no clips for this detector
        
        return None
    
    scores, call_counts = reduce_size(line_name, call_counts)
    _, total_counts = reduce_size(line_name, total_counts)
    
    # Trim counts as needed to avoid divides by zero in precision
    # computations.
    indices = np.where(total_counts == 0)[0]
    if len(indices) != 0:
        end = indices[0]
        call_counts = call_counts[:end]
        total_counts = total_counts[:end]
        
    precisions = 100 * call_counts / total_counts.astype('float')

    show_precision_table(line_name, scores, precisions)
    
    return call_counts, precisions
       

def show_precision_table(line_name, scores, precisions):
    
    print(line_name, 'precision vs. threshold:')
    
    min_score = \
        MIN_PLOT_LINE_SCORES.get(line_name, DEFAULT_MIN_PLOT_LINE_SCORE)
        
    num_scores = 100 - min_score
    
    f = '{:.0f},{:.1f}'
    
    # Show precision for scores from `min_score` through 99.
    for i in range(num_scores):
        print(f.format(scores[i], precisions[i]))
        
    # Show precision for score of 100.
    print(f.format(scores[-1], precisions[-1]))
       

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


def reduce_size(line_name, clip_counts):
    
    """
    Reduce the size of the specified clip counts by removing counts
    at non-integer scores below 99.
    
    For scores from the minimum to 99 a score resolution of 1 has
    been fine for (mostly) keeping our curves from looking like the
    piecewise linear approximations that they are. We need higher
    resolution between 99 and 100, however, to accomplish the same
    goal there.
    """
    
    min_score = \
        MIN_PLOT_LINE_SCORES.get(line_name, DEFAULT_MIN_PLOT_LINE_SCORE)
    percent_size = 10 ** NUM_SCORE_DECIMAL_PLACES
    
    start = np.arange(min_score, 99, dtype='float64')
    end = 99 + np.arange(percent_size + 1) / float(percent_size)
    scores = np.concatenate((start, end))

    m = min_score * percent_size
    n = 99 * percent_size
    start = clip_counts[m:n:percent_size]
    end = clip_counts[n:]
    counts = np.concatenate((start, end))
    
    return scores, counts
    

def create_matplotlib_plot_marker(
        axes, marker_name, detector_name, marker_color, old_bird_clip_counts):

    call_count, noise_count = old_bird_clip_counts[detector_name]
    precision = 100 * call_count / (call_count + noise_count)
    axes.scatter(call_count, precision, c=marker_color, label=marker_name)
    
    
def create_bokeh_plots(clip_counts, old_bird_clip_counts):
        
    summed_clip_counts = sum_clip_counts(clip_counts)
    summed_old_bird_clip_counts = \
        sum_old_bird_clip_counts(old_bird_clip_counts)
    
    # Create plot for all station/nights.
    file_path = PLOTS_DIR_PATH / ALL_STATION_NIGHTS_PLOT_FILE_NAME
    create_bokeh_plot(
        file_path, 'All Station-Nights', summed_clip_counts,
        summed_old_bird_clip_counts)
    
    if CREATE_SEPARATE_STATION_NIGHT_PLOTS:
        
        station_nights = sorted(clip_counts.keys())
            
        for station_night in station_nights:
            
            file_path = create_bokeh_plot_file_path(*station_night)
            title = '{} / {}'.format(*station_night)
            counts = clip_counts[station_night]
            old_bird_counts = old_bird_clip_counts[station_night]
            create_bokeh_plot(file_path, title, counts, old_bird_counts)
        

def create_bokeh_plot(file_path, title, clip_counts, old_bird_clip_counts):

    output_file(file_path)
    
    tools = 'save'
    # tools = 'hover,save,pan,box_zoom,reset,wheel_zoom'
    
    p = figure(plot_width=700, plot_height=700, tools=tools)
    
    # Create plot lines.
    for line_name, (detector_names, line_color) in PLOT_LINE_DATA.items():
        create_bokeh_plot_line(
            p, line_name, detector_names, line_color, clip_counts)
        
    # Create Old Bird markers.
    for marker_name, (detector_name, marker_color) in \
            OLD_BIRD_PLOT_DATA.items():
        
        create_bokeh_plot_marker(
            p, marker_name, detector_name, marker_color, old_bird_clip_counts)
         
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
    
    data = get_plot_line_data(line_name, detector_names, clip_counts)
    
    if data is not None:
        
        call_counts, precisions = data
        
        p.line(
            call_counts, precisions, legend=line_name,
            line_color=line_color, line_width=2)
          
              
def create_bokeh_plot_marker(
        p, marker_name, detector_name, marker_color, old_bird_clip_counts):
    
    call_count, noise_count = old_bird_clip_counts[detector_name]
    precision = 100 * call_count / (call_count + noise_count)
    p.circle(
        call_count, precision, size=10, color=marker_color, legend=marker_name)

    
def create_bokeh_plot_file_path(station_name, date):
    file_name = BOKEH_PLOT_FILE_NAME_FORMAT.format(station_name, date)
    return PLOTS_DIR_PATH / file_name


if __name__ == '__main__':
    main()
