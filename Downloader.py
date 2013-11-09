# coding=utf-8
from Video import Video
import utils


class Downloader(object):
    def __init__(self, search_terms, directory):
        self.prefetch = False

        self.videos = self.get_next_10_videos()
        self.current_video = None
        self.current_video_index = 0

        self.search_terms = search_terms
        self.directory = directory

    def get_next_10_videos(self):
        videos = []

        start_index = len(self.videos)
        entries = self.get_entries(start_index)

        for (index, entry) in enumerate(entries, start_index):
            video = Video(entry, index, self.directory)
            videos.append(video)

        return videos

    def get_entries(self, start_index):
        json = utils.download_json(self.search_terms, start_index)
        return utils.get_entries(json)

    def is_downloading(self):
        return self.current_video and self.current_video.is_downloading()

    def set_prefetching_download_speed(self):
        self.prefetch = True

    def set_full_download_speed(self):
        self.prefetch = False

    def download_next_video(self):
        self.current_video_index += 1
        self.download_video()

    def download_video(self):
        video = self.get_video()
        video.download()

    def get_video(self):
        if self.must_get_new_videos():
            self.videos.extend(self.get_next_10_videos())

        return self.videos[self.current_video_index]

    def must_get_new_videos(self):
        return self.current_video_index >= len(self.videos)

    def stop_download(self):
        if self.is_downloading():
            self.current_video.stop_downloading()

    def download(self, index):
        pass

    def start_prefetching_future_videos(self):
        pass

    def is_there_video_to_download(self):
        pass

    def get_current_video_url(self):
        return self.current_video.get_url()

    def get_current_video_file_path(self):
        return self.current_video.get_video_path()

    def get_current_video_title(self):
        return self.current_video.get_title()

    def get_current_video_length(self):
        return self.current_video.get_length()