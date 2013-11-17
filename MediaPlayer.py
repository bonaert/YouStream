# coding=utf-8
import Queue


class MediaPlayer(object):
    def __init__(self, mplayer_controller):
        self.media_player = mplayer_controller
        self.is_paused = False
        self.current_video_path = None

    def is_video_playing(self):
        return self.media_player.playing

    def is_video_paused(self):
        return self.is_paused

    def get_current_video_path(self):
        return self.current_video_path

    def pause(self):
        if self.is_playing:
            self.invert_player_paused_state()
            self.is_paused = True

    def unpause(self):
        if not self.is_playing:
            self.invert_player_paused_state()
            self.is_paused = False

    def invert_player_paused_state(self):
        self.media_player.Pause()

    def reset(self):
        self.media_player.Seek(0, type_=1)

    def play_file(self, path):
        #if not self.mediaPlayer:
        # todo: don't forget to see what this line was for
        # todo: make notes about decisions
        # self.mediaPlayer.Quit()
        #self.mediaPlayer.Start()
        self.media_player.Loadfile(path)
        self.current_video_path = path
        self.is_playing = True
        self.is_paused = False

    def loop_file(self, path):
        self.play_file(path)
        self.media_player.Loop(0)

    def get_current_video_time_position(self):
        try:
            return int(self.media_player.GetTimePos())
        except ValueError, Queue.Empty:
            pass

    def get_current_video_length(self):
        try:
            return int(self.media_player.GetTimeLength())
        except ValueError, Queue.Empty:
            return 0

    def destroy(self):
        self.media_player.Quit()

    def play_current_video_at_time_position(self, path, video_time_position):
        self.play_file(path)
        self.media_player.Seek(video_time_position, type_=2)