# coding=utf-8
import os
import time
import subprocess

from multiprocessing.pool import ThreadPool


class Video(object):
    def __init__(self, metadata_entry, index, directory, max_download_rate=200):
        self.author = self.get_author_from_metadata(metadata_entry)
        self.title = self.get_title_from_metadata(metadata_entry)
        self.url = self.get_url_from_metadata(metadata_entry)
        self.date = self.get_date_from_metadata(metadata_entry)
        self.length = self.get_length_from_metadata(metadata_entry)
        self.index = index

        self.is_downloading = False
        self.pool = None
        self.download_subprocess = None
        self.max_download_rate = max_download_rate
        self.is_prefetching = False
        self.is_downloaded = False

        self.directory = directory
        self.file_path = None

    def get_author_from_metadata(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'author', 0, 'name', '$t')

    def get_title_from_metadata(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'media$group', 'media$title', '$t')

    def get_url_from_metadata(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'link', 0, 'href')

    def get_date_from_metadata(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'updated', '$t')

    def get_length_from_metadata(self, metadata_entry):
        length = self.try_to_get_attribute(metadata_entry, 'media$group', 'yt$duration', 'seconds')
        if length:
            return int(length)

        length = self.try_to_get_attribute(metadata_entry, 'media$group', 'media$content', 0, 'duration')
        if length:
            return int(length)

    def try_to_get_attribute(self, entry, *args):
        """
        Given various attributes, tries extract them from the entry.
        Example: try_to_get_attribute(entry, 'data', 'result', 'length') tries
        to return entry['data']['result']['length']. Simple method to handle the
        necessary exception handling behind the scenes. If there is an error,
        None is returned.
        """
        try:
            result = entry
            for arg in args:
                result = result[arg]
            return result
        except AttributeError:
            return None

    def set_prefetching(self):
        self.is_prefetching = True

    def set_full_download_speed(self):
        self.is_prefetching = False

    def get_index(self):
        return self.index

    def get_url(self):
        return self.url

    def get_title(self):
        return self.title

    def get_length(self):
        return self.length

    def get_file_path(self):
        self.check_download_has_started()
        return self.file_path

    def download(self):
        if not self.is_downloaded:
            self.start_download()

    def start_download(self):
        self.is_downloading = True
        self.pool = ThreadPool(processes=1)
        self.pool.apply_async(self.download_video, callback=self.close_subprocess)
        self.pool.close()

    def download_video(self):
        self.file_path = self.get_incomplete_file_path()
        print("Got path:", self.file_path)

        print("Starting download process")
        self.start_download_subprocess()
        print("Process started. Waiting!")
        self.download_subprocess.wait()
        print("Wait is over. Download ended")

    def get_incomplete_file_path(self):
        return "%s%s.mp4.part" % (self.directory, self.title)

    def start_download_subprocess(self):
        args = self.get_download_process_arguments()
        self.download_subprocess = subprocess.Popen(args)

    def get_download_process_arguments(self):
        args = ["youtube-dl"]
        args.extend(['--output', self.get_output_file_template()])
        args.extend(['-f', 'mp4'])
        args.extend(['-r', self.get_download_rate_param()])
        args.append(self.url)
        return args

    def get_output_file_template(self):
        return self.directory + '%(title)s.mp4'

    def get_download_rate_param(self):
        if self.is_prefetching:
            return "%dk" % self.max_download_rate
        else:
            return "%dk" % (self.max_download_rate // 2)

    def close_subprocess(self):
        self.is_downloading = False
        self.is_downloaded = True

        self.file_path = self.get_finished_file_path()

        self.download_subprocess = None
        self.pool = None

    def get_finished_file_path(self):
        return "%s%s.mp4" % (self.directory, self.title)

    def stop_downloading(self):
        raise NotImplementedError

    def is_file_size_greater_than(self, path, size):
        return self.is_downloading and os.path.exists(path) and os.path.getsize(path) > size

    def wait_while_file_is_small(self, size):
        self.check_download_has_started()
        self.wait_while_file_is_smaller_than(size)

    def wait_while_file_is_smaller_than(self, size, interval=0.3):
        while not self.is_downloaded and not self.is_file_size_greater_than(self.file_path, size):
            time.sleep(interval)
            print("File is still too small")

    def has_been_downloaded(self):
        return self.is_downloaded

    def get_file_size(self):
        self.check_download_has_started()
        return os.path.getsize(self.file_path)

    def check_download_has_started(self):
        if not (self.is_downloaded or self.is_downloading):
            raise Exception("Download has not started")

    def has_file_been_created(self):
        return self.is_downloading or self.is_downloaded