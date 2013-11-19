# coding=utf-8
import time
import utils
import wx

from Downloader import Downloader


TIMER_INTERVAL = 0.1


class PlayerManager(object):
    def __init__(self, media_player, directory=None):
        # Download
        self.downloader = None

        # Player
        self.length = None
        self.video_time_position = 0
        self.current_video_index = 0

        self.directory = utils.make_directory(directory)
        self.media_player = media_player

    def open(self, path):
        self.play_file(path)

    def on_media_started(self):
        self.video_time_position = 0
        self.length = self.get_current_video_length()
        print("Length of file: %d" % self.length)

    def on_media_finished(self):
        self.length = 0

    def on_previous(self):
        is_first_song = self.is_playing_first_song()
        if not is_first_song:
            self.start_download(self.current_video_index - 1)
            self.play_current_video_when_big_enough()

    def on_pause(self):
        self.media_player.pause()

    def on_play(self):
        self.media_player.unpause()

    def on_reset(self):
        self.media_player.reset()

    def on_next(self):
        self.start_download(self.current_video_index + 1)
        self.play_current_video_when_big_enough()

    def on_search(self, search_terms):
        self.downloader = self.build_downloader(search_terms)
        self.download_first_video()
        self.play_current_video_when_big_enough()

    def on_timer(self):
        pass

    def must_restart_video(self):
        is_downloading = self.downloader and self.downloader.is_downloading()
        return not self.is_video_playing() and is_downloading and self.get_current_video_time_position() > 2


    # Media player

    def is_video_playing(self):
        return self.media_player.is_video_playing()

    def play_current_video_when_big_enough(self):
        self.downloader.wait_while_current_video_is_small()
        self.play_current_video()

    def play_current_video(self):
        path = self.downloader.get_current_video_file_path()
        self.play_file(path)

    def play_file(self, path):
        self.media_player.play_file(path)

    def raise_error_window(self, path):
        message = "Unable to load %s: Unsupported format?" % path
        wx.MessageBox(message, "ERROR", wx.ICON_ERROR | wx.OK)

    def restart_video(self):
        path = self.downloader.get_current_video_file_path()
        self.media_player.play_current_video_at_time_position(path, self.video_time_position)


    # Downloader

    def build_downloader(self, search_terms):
        return Downloader(search_terms, self.directory)

    def download_first_video(self):
        self.start_download(0)

    def start_download(self, index):
        self.current_video_index = index
        self.downloader.download_video_with_index(index)
        time.sleep(2)


    # Getters and setters

    def is_playing_first_song(self):
        return self.current_video_index == 0

    def get_current_video_length(self):
        if self.downloader:
            return self.downloader.get_current_video_length()
        else:
            return self.media_player.get_current_video_length()

    def get_current_video_time_position(self):
        return self.media_player.get_current_video_time_position() or self.get_approximate_video_time_position()

    def get_approximate_video_time_position(self):
        if self.video_time_position:
            return self.video_time_position + TIMER_INTERVAL
        else:
            return 0

    def get_current_video_file_path(self):
        return self.downloader.get_current_video_file_path()



    def destroy(self):
        self.media_player.destroy()

    def is_downloading(self):
        return self.downloader and self.downloader.is_downloading()