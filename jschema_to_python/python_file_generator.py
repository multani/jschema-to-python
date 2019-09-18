import os

class PythonFileGenerator(object):
    def __init__(self, output_directory):
        self.output_directory = output_directory
        self.file_obj = None

    def write_generation_comment(self):
        self.write_formatted_line('# This file was generated by {}.', __package__)
        self.file_obj.write('\n')

    def write_formatted_line(self, line, *args):
        self.file_obj.write(line.format(*args) + '\n')

    def make_output_file_path(self, file_name):
        return os.path.join(self.output_directory, file_name)