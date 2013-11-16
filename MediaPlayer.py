# coding=utf-8


class MediaPlayer(object):
    def __init__(self, media_player):
        self.media_player = media_player
        self.is_playing = False
        self.current_video_path = None

    def is_video_playing(self):
        return self.is_playing

    def get_current_video_path(self):
        return self.current_video_path

    def pause(self):
        if self.is_playing:
            self.invert_player_paused_state()
            self.is_playing = False

    def unpause(self):
        if not self.is_playing:
            self.invert_player_paused_state()
            self.is_playing = True

    def invert_player_paused_state(self):
        self.media_player.Pause()

    def reset(self):
        self.media_player.Seek(0, type_=0)

    def play_file(self, path):
        print("Playing: ", path)
        #if not self.mediaPlayer:
        # todo: don't forget to see what this line was for
        # todo: make notes about decisions
        # self.mediaPlayer.Quit()
        #self.mediaPlayer.Start()
        self.media_player.Loadfile(path)
        #if loop:
        #   self.mediaPlayer.Loop(0)

        self.current_video_path = path
        self.is_playing = True
