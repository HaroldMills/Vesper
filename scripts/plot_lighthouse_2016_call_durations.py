"""Plots call duration histograms and cumulative plots from a clips CSV."""

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter, NullFormatter
from matplotlib.widgets import RadioButtons


DIR_PATH = Path(
    '/Users/harold/Desktop/Lighthouse Tseep Detector/'
    'Lighthouse 2016 Call Durations')
FILE_PATH = DIR_PATH / 'Lighthouse 2016 Clips.csv'
LONG_CALLS_FILE_PATH = DIR_PATH / 'Lighthouse 2016 Long Calls.csv'
PDF_FILE_PATH = DIR_PATH / 'Lighthouse 2016 Call Durations.pdf'
SAMPLE_RATE = 22050
LONG_CALL_DURATION_THRESHOLD = .25


def print_rows(title, rows, fieldnames):
    print(f'{title} ({len(rows)}):')
    for row in rows:
        print('    ' + ','.join(row[name] for name in fieldnames))
    print()


def write_rows(file_path, fieldnames, rows, sort_key):
    rows = sorted(rows, key=lambda r: r[sort_key], reverse=True)
    fieldnames = fieldnames + ['call_duration']
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows)} rows to {file_path}.')


def main():

    file_path = sys.argv[1] if len(sys.argv) > 1 else FILE_PATH

    call_durations_by_classification = {}
    long_call_rows = []
    negative_call_rows = []
    unspecific_call_rows = []
    with open(file_path, newline='') as f:

        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:

            row['call_duration'] = None

            if row['classification'] == 'Call':
                unspecific_call_rows.append(row)

            start = row['call_start_index'].strip()
            end = row['call_end_index'].strip()

            # Skip calls with missing indices (empty or "NULL").
            if start.isdigit() and end.isdigit():

                call_duration = (int(end) - int(start)) / SAMPLE_RATE
                row['call_duration'] = call_duration

                if call_duration < 0:
                    negative_call_rows.append(row)
                call_durations_by_classification.setdefault(
                    row['classification'], []).append(call_duration)

                if call_duration > LONG_CALL_DURATION_THRESHOLD:
                    long_call_rows.append(row)

    call_count = sum(len(d) for d in call_durations_by_classification.values())
    print(f'Total number of calls: {call_count}')
    print()

    write_rows(
        LONG_CALLS_FILE_PATH, fieldnames, long_call_rows, 'call_duration')
    print()

    print_rows('Rows with negative call duration', negative_call_rows, fieldnames)
    print_rows(
        'Rows with classification "Call"', unspecific_call_rows, fieldnames)

    create_classification_plots(call_durations_by_classification)

    plt.show()


def plot_histogram(ax, durations, title):
    counts, edges, _ = ax.hist(durations, bins=50, log=True)
    ax.set_title(title)
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Number of calls')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:g}'))
    ax.yaxis.set_minor_formatter(NullFormatter())
    return counts, edges


def plot_cumulative(ax, durations, title):
    sorted_durations = sorted(durations)
    fractions = [(i + 1) / len(sorted_durations)
                 for i in range(len(sorted_durations))]
    ax.step(sorted_durations, fractions, where='post')
    ax.set_title(title)
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Fraction of calls with duration \u2264 x')
    ax.set_ylim(0, 1)
    ax.grid(True)


def plot_choice(hist_ax, cumulative_ax, durations, choice):
    hist_ax.clear()
    cumulative_ax.clear()
    plot_histogram(hist_ax, durations, f'Call Durations: {choice}')
    plot_cumulative(
        cumulative_ax, durations, f'Cumulative Call Durations: {choice}')
    hist_ax.set_xlim(0, .5)
    cumulative_ax.set_xlim(0, .5)


def write_pdf(durations_by_name):

    """Writes the plots for each choice to its own page of a PDF file."""

    with PdfPages(PDF_FILE_PATH) as pdf:
        for choice, durations in durations_by_name.items():
            fig, axes = plt.subplots(2, 1, figsize=(8, 10))
            plot_choice(axes[0], axes[1], durations, choice)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
    print(f'Wrote {len(durations_by_name)} pages to {PDF_FILE_PATH}.')


def create_classification_plots(durations_by_classification):

    """
    Creates a histogram and a cumulative plot of the call durations of a
    single classification, or of all calls.

    The plot window includes radio buttons for selecting the
    classification to display. The plots for all choices are also
    written to a PDF file, one choice per page.
    """

    # The "All" choice replaces the unspecific "Call" classification and
    # includes the durations of all calls, regardless of classification.
    durations_by_name = {
        'All': [d for ds in durations_by_classification.values() for d in ds]}

    # Menu labels omit the "Call." prefix of classifications.
    for classification in sorted(durations_by_classification):
        if classification != 'Call':
            name = classification.replace('Call.', '')
            durations_by_name[name] = \
                durations_by_classification[classification]

    names = list(durations_by_name)

    write_pdf(durations_by_name)

    fig = plt.figure(figsize=(12, 8))
    hist_ax = fig.add_axes([.35, .57, .62, .33])
    cumulative_ax = fig.add_axes([.35, .08, .62, .33])

    # The widget is attached to the figure so it is not garbage collected.
    menu_ax = fig.add_axes([.05, .08, .2, .84])
    menu = RadioButtons(menu_ax, names, active=0)
    for label in menu.labels:
        label.set_fontsize(8)

    def on_menu_clicked(choice):
        plot_choice(hist_ax, cumulative_ax, durations_by_name[choice], choice)
        fig.canvas.draw_idle()

    on_menu_clicked(names[0])
    menu.on_clicked(on_menu_clicked)
    fig.widgets = (menu,)


if __name__ == '__main__':
    main()
