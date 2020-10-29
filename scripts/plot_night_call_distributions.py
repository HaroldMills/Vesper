"""
Script that plots nightly NFC temporal distributions.

The script plots distributions for three nights and three detectors
for data collected at the Harold monitoring station from October 21-23,
2020.

The script expects several CSV input files, each containing clip metadata
for one detector and all three nights. The files were created using
Vesper's "Export clip metadata to CSV file" command.

I initially plotted cumulative distributions of data binned by the
minute, but later decided to plot non-cumulative distributions binned
by the hour. Non-cumulative distributions binned by the minute were
too noisy. The code for plotting cumulative distributions is still
present, but calls to it are commented out.
"""


from collections import defaultdict
from pathlib import Path
import csv
import datetime

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.dates import DateFormatter, HourLocator
import matplotlib.pyplot as plt
import numpy as np


DATA_DIR_PATH = Path('/Users/harold/Desktop/Tseeps')
CSV_FILE_NAME_FORMAT = 'Tseeps_{}.csv'
PDF_FILE_NAME = 'Harold Tseep Call Densities.pdf'

DETECTORS = [
    ('OB', 'Old Bird Tseep Detector Redux 1.1'),
    ('MPG', 'MPG Ranch Tseep Detector 1.0 60'),
    ('BVD', 'BirdVoxDetect 0.2.3 AT 30')
]

DETECTOR_KEYS = tuple(d[0] for d in DETECTORS)

DETECTOR_NAMES = tuple(d[1] for d in DETECTORS)

NIGHTS = tuple(datetime.date(*d) for d in (
    (2020, 10, 20),
    (2020, 10, 21),
    (2020, 10, 22)
))

START_TIME_INDEX = 10

ONE_DAY = datetime.timedelta(days=1)

FIRST_BIN_TIME = datetime.time(hour=19)
BIN_COUNT = 720
HOURLY_BIN_COUNT = 12


def main():
    
    start_time_lists = get_clip_start_time_lists()
    start_time_densities = get_hourly_start_time_densities(start_time_lists)
    # start_time_cdfs = get_start_time_cdfs(start_time_lists)
    
    pdf_file_path = DATA_DIR_PATH / PDF_FILE_NAME
    with PdfPages(pdf_file_path) as pdf:
        create_density_plots(pdf, start_time_densities)
        # create_cdf_plots(pdf, start_time_cdfs)
    
    
def get_clip_start_time_lists():
    
    counts = defaultdict(list)
    
    for detector_key in DETECTOR_KEYS:
            
        file_path = get_csv_file_path(detector_key)
        
        with open(file_path) as file_:
            reader = csv.reader(file_)
            lines = [line for line in reader][1:]
            start_times = [get_start_time(line) for line in lines]
            
        for start_time in start_times:
            night = get_night(start_time)
            
            counts[(detector_key, night)].append(start_time)
            
    return counts
    
    
def get_csv_file_path(detector_key):
    file_name = CSV_FILE_NAME_FORMAT.format(detector_key)
    return DATA_DIR_PATH / file_name


def get_start_time(line):
    start_time = line[START_TIME_INDEX]
    start_time = datetime.datetime.strptime(start_time, '%m/%d/%y %H:%M:%S')
    return start_time


def get_night(start_time):
    night = start_time.date()
    if start_time.hour < 12:
        night = night - ONE_DAY
    return night
        
        
def get_hourly_start_time_densities(start_time_lists):
    return dict(
        (key, get_hourly_start_time_density(times, key[1]))
        for key, times in start_time_lists.items())
    
    
def get_hourly_start_time_density(start_times, night):
    
    first_bin_time = datetime.datetime.combine(night, FIRST_BIN_TIME)
    
    bin_times = get_hourly_bin_times(first_bin_time)
    
    counts = np.zeros(HOURLY_BIN_COUNT)
    
    for time in start_times:
        
        bin_num = get_hourly_bin_num(time, first_bin_time)
        
        if bin_num < BIN_COUNT:
            counts[bin_num] += 1
            
    total_count = counts.sum()
    density = counts / total_count
    
    return bin_times, density
    
    
def get_hourly_bin_times(first_bin_time):
    return [
        first_bin_time + datetime.timedelta(hours=i)
        for i in range(HOURLY_BIN_COUNT)]
    
    
def get_hourly_bin_num(time, first_bin_time):
    delta = time - first_bin_time
    return int(delta.total_seconds() // 3600)
    
    
def get_start_time_cdfs(start_time_lists):
    return dict(
        (key, get_start_time_cdf(times, key[1]))
        for key, times in start_time_lists.items())
    

def get_start_time_cdf(start_times, night):
    
    first_bin_time = datetime.datetime.combine(night, FIRST_BIN_TIME)
    
    bin_times = get_bin_times(first_bin_time)
    
    counts = np.zeros(BIN_COUNT)
    
    for time in start_times:
        
        bin_num = get_bin_num(time, first_bin_time)
        
        if bin_num < BIN_COUNT:
            counts[bin_num] += 1
    
    counts = np.cumsum(counts)
    cdf = counts / counts[-1]
    
    return bin_times, cdf


def get_bin_times(first_bin_time):
    return [
        first_bin_time + datetime.timedelta(minutes=i)
        for i in range(BIN_COUNT)]
    
    
def get_bin_num(time, first_bin_time):
    delta = time - first_bin_time
    return int(delta.total_seconds() // 60)
    
    
def create_density_plots(pdf, start_time_densities):
    
    plot_detector_start_time_densities(pdf, start_time_densities, 0)
    
    for night in NIGHTS:
        plot_night_start_time_densities(pdf, start_time_densities, night)


def plot_detector_start_time_densities(
        pdf, start_time_densities, detector_num):
    
    detector_key, detector_name = DETECTORS[detector_num]
    
    for night in NIGHTS:
        bin_times, density = start_time_densities[(detector_key, night)]
        bin_times = adjust_bin_time_dates(bin_times, NIGHTS[0], night)
        plot(bin_times, density, 'Call Density')
        plt.title(f'{detector_name} Call Densities')
        
    plt.legend(NIGHTS)
    pdf.savefig()
    plt.close()
    
 
def adjust_bin_time_dates(bin_times, desired_date, date):
    delta = desired_date - date
    return [dt + delta for dt in bin_times]
    
    
def plot_night_start_time_densities(pdf, start_time_densities, night):
    
    for detector_key in DETECTOR_KEYS:
        bin_times, cdf = start_time_densities[(detector_key, night)]
        plot(bin_times, cdf, 'Call Density')
        plt.title(f'{str(night)} Call Densities')
        
    plt.legend(DETECTOR_NAMES)
    pdf.savefig()
    plt.close()
    
    
def create_cdf_plots(pdf, start_time_cdfs):
    
    plot_detector_start_time_cdfs(pdf, start_time_cdfs, 0)
    
    for night in NIGHTS:
        plot_night_start_time_cdfs(pdf, start_time_cdfs, night)


def plot_detector_start_time_cdfs(pdf, start_time_cdfs, detector_num):
    
    detector_key, detector_name = DETECTORS[detector_num]
    
    for night in NIGHTS:
        bin_times, cdf = start_time_cdfs[(detector_key, night)]
        bin_times = adjust_bin_time_dates(bin_times, NIGHTS[0], night)
        plot(bin_times, cdf, 'Cumulative Call Density')
        plt.title(f'{detector_name} Cumulative Call Densities')
        
    plt.legend(NIGHTS)
    pdf.savefig()
    plt.close()
    
 
def plot_night_start_time_cdfs(pdf, start_time_cdfs, night):
    
    for detector_key in DETECTOR_KEYS:
        bin_times, cdf = start_time_cdfs[(detector_key, night)]
        plot(bin_times, cdf, 'Cumulative Call Density')
        plt.title(f'{str(night)} Harold Tseep CDFs')
        
    plt.legend(DETECTOR_NAMES)
    pdf.savefig()
    plt.close()
    
    
def plot(bin_times, y, y_axis_label):
    
    plt.plot(bin_times, y)
    
    axes = plt.gca()
    locator = HourLocator()
    formatter = DateFormatter('%H')
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(formatter)
    
    axes.set_xlabel('Hour')
    axes.set_ylabel(y_axis_label)
    
    axes.grid()
        

if __name__ == '__main__':
    main()
