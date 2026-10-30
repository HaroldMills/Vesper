from pathlib import Path
import csv
import logging
import tempfile

from vesper.command.command import CommandExecutionError, CommandSyntaxError
from vesper.django.app.models import AnnotationInfo, Processor, TagInfo
from vesper.singleton.archive import archive
import vesper.django.app.model_utils as model_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


_logger = logging.getLogger()


# TODO: Add type checking to functions that get arguments.


def get_required_arg(name, args):
    try:
        return args[name]
    except KeyError:
        raise CommandSyntaxError(
            f'Missing required command argument "{name}".')


def get_optional_arg(name, args, default=None):
    return args.get(name, default)


def get_station_mic_output_pairs(ui_names):

    pairs_dict = model_utils.get_station_mic_output_pairs_dict()

    pairs = set()

    for name in ui_names:

        pair = pairs_dict.get(name)

        if pair is None:
            raise CommandExecutionError(
                f'Unrecognized station / mic output UI name "{name}".')

        else:
            pairs.add(pair)

    return sorted(pairs)


def get_timing_text(elapsed_time, item_count, items_name):
    
    # Round elapsed time to nearest tenth of a second since it
    # will be displayed at that resolution. This will keep the
    # reported item count, elapsed time, and rate consistent.
    elapsed_time = round(10 * elapsed_time) / 10
    
    time_text = f' in {elapsed_time:.1f} seconds'
    
    if elapsed_time > 0:
        
        rate = item_count / elapsed_time
        return f'{time_text}, an average of {rate:.1f} {items_name} per second'
        
    else:
        # elapsed time is zero
        
        return time_text


def write_csv_file(file_path, rows, header=None):
    
    handle_error = handle_command_execution_error

    # Create output CSV file in temporary file directory.
    try:
        temp_file = tempfile.NamedTemporaryFile(
            'wt', newline='', prefix='vesper-', suffix='.csv',
            delete=False)
    except Exception as e:
        handle_error('Could not open output CSV file.', e)
    
    # Create CSV writer.
    try:
        writer = csv.writer(temp_file)
    except Exception as e:
        handle_error('Could not create CSV file writer.', e)

    # Write header.
    if header is not None:
        try:
            writer.writerow(header)
        except Exception as e:
            handle_error('Could not write CSV file header.', e)

    # Write rows.
    try:
        writer.writerows(rows)
    except Exception as e:
        handle_error('Could not write CSV file rows.', e)

    temp_file_path = Path(temp_file.name)
    
    # Close output file.
    try:
        temp_file.close()
    except Exception as e:
        handle_error('Could not close output CSV file.', e)
    
    # Copy temporary output file to final path.
    try:
        os_utils.copy_file(temp_file_path, file_path)
    except Exception as e:
        handle_error('Could not copy temporary CSV file to final path.', e)


def handle_command_execution_error(message, exception):
    raise CommandExecutionError(
        f'{message} Error message was: {str(exception)}.')


def log_and_reraise_fatal_exception(exception, action_text, result_text=None):
    
    error = _logger.error
    
    error(f'{action_text} failed with an exception.')
    error(f'The exception message was:')
    error(f'    {str(exception)}')
    
    if result_text is not None:
        error(result_text)
        
    raise


def get_or_create_processor(name, type, description):
    
    processor, created = Processor.objects.get_or_create(
        name=name, type=type, defaults={'description': description})
      
    if created:
        _logger.info(f'Created processor "{name}" of type "{type}".')
        archive.refresh_processor_cache()
    
    return processor


def get_required_annotation_info(name):

    try:
        return AnnotationInfo.objects.get(name=name)
    
    except AnnotationInfo.DoesNotExist:
        _logger.error(
            f'Required annotation info for annotation "{name}" is missing '
            f'from archive database.')
        return None

    
def get_or_create_annotation_info(
        name,
        type,
        description,
        constraint=None,
        creation_time=None,
        creating_user=None,
        creating_job=None):

    if creation_time is None:
        creation_time = time_utils.get_utc_now()

    info, created = AnnotationInfo.objects.get_or_create(
        name=name,
        defaults={
            'type': type,
            'description': description,
            'constraint': constraint,
            'creation_time': creation_time,
            'creating_user': creating_user,
            'creating_job': creating_job
        }
    )

    if created:
        _logger.info(
            f'Created annotation info for annotation "{name}" of type '
            f'"{type}".')

    return info


def get_required_tag_info(name):

    try:
        return TagInfo.objects.get(name=name)
    except TagInfo.DoesNotExist:
        _logger.error(
            f'Required tag info for tag "{name}" is missing '
            f'from archive database.')
        return None

    
def get_or_create_tag_info(
        name,
        description,
        creation_time=None,
        creating_user=None,
        creating_job=None):

    if creation_time is None:
        creation_time = time_utils.get_utc_now()

    info, created = TagInfo.objects.get_or_create(
        name=name,
        defaults={
            'description': description,
            'creation_time': creation_time,
            'creating_user': creating_user,
            'creating_job': creating_job
        }
    )

    if created:
        _logger.info(f'Created tag info for tag "{name}".')

    return info
