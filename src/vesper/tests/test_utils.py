import os.path


def get_test_data_dir_path(module_file_path):
    tests_dir_path, file_name = os.path.split(module_file_path)
    module_name = file_name[:-len('.py')]
    return os.path.join(tests_dir_path, 'data', module_name)
