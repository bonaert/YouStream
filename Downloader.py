# coding=utf-8
import utils
from Video import Video


DEFAULT_SIZE = 2 * 1024 ** 2  # 2 MB


class Downloader(object):
    def __init__(self, search_terms, directory):
        self.prefetch = False

        self.search_terms = search_terms
        self.directory = directory

        self.videos = []
        self.videos = self.get_next_10_videos()
        self.current_video = None
        self.current_video_index = 0

    def get_next_10_videos(self):
        videos = []

        start_index = self.get_current_number_of_videos()
        entries = self.get_entries(start_index)

        for (index, entry) in enumerate(entries, start_index):
            video = Video(entry, index, self.directory)
            videos.append(video)

        return videos

    def get_current_number_of_videos(self):
        try:
            return len(self.videos)
        except AttributeError:
            return 0

    def get_entries(self, start_index):
        json = utils.download_json(self.search_terms, start_index)
        return utils.get_entries(json)

    def is_downloading(self):
        return self.current_video and self.current_video.is_downloading

    def get_current_video_url(self):
        return self.current_video.get_url()

    def get_current_video_file_path(self):
        return self.current_video.get_file_path()

    def get_current_video_title(self):
        return self.current_video.get_title()

    def get_current_video_length(self):
        return self.current_video.get_length()

    def get_current_video_index(self):
        return self.current_video_index

    def set_prefetching_download_speed(self):
        self.prefetch = True

    def set_full_download_speed(self):
        self.prefetch = False

    def download_next_video(self):
        self.download_video_with_index(self.current_video_index + 1)

    def download_video_with_index(self, index):
        if index < 0:
            raise Exception("Negative index: %d" % index)

        self.current_video_index = index
        self.download_current_video()

    def download_current_video(self):
        video = self.get_current_video()

        if video != self.current_video:
            self.stop_download()

        self.current_video = video

        if not video.has_been_downloaded():
            video.download()

    def get_current_video(self):
        if self.must_get_new_videos():
            self.videos.extend(self.get_next_10_videos())

        return self.videos[self.current_video_index]

    def must_get_new_videos(self):
        return self.current_video_index >= len(self.videos)

    def stop_download(self):
        if self.is_downloading():
            self.current_video.stop_downloading()

    def is_there_video_to_download(self):
        if not self.must_get_new_videos():
            return True

        new_videos = self.get_next_10_videos()
        if new_videos:
            self.videos.extend(new_videos)
        else:
            return False

    def is_video_already_downloaded(self, index):
        return 0 < index < len(self.videos) and self.videos[index].has_been_downloaded()

    def is_video_downloading(self, index):
        return 0 < index < len(self.videos) and self.videos[index].is_downloading()

    def get_file_path_of_video_with_index(self, index):
        self.check_index(index)

        if not self.videos[index].has_file_been_created():
            raise Exception("File with index %d has not been created." % index)

        return self.videos[index].get_file_path()

    def check_index(self, index):
        if not (0 <= index < len(self.videos)):
            raise Exception("Invalid index: %d" % index)
        else:
            print("0 < %d < %d" % (index, len(self.videos)))

    def wait_while_video_is_small(self, index, size=DEFAULT_SIZE):
        self.check_index(index)
        self.videos[index].wait_while_file_is_small(size)

    def wait_while_current_video_is_small(self, size=DEFAULT_SIZE):
        self.current_video.wait_while_file_is_small(size)

    def destroy(self):
        self.stop_download()