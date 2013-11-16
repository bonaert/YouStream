# coding=utf-8
import os
import wx

import MplayerCtrl as mpc
from MediaPlayer import MediaPlayer
import utils


DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 800


class Player(wx.Frame):
    def __init__(self, directory=None):
        super(Player, self).__init__(parent=None, title="YouStream",
                                     size=(DEFAULT_WIDTH, DEFAULT_HEIGHT))

        # Download
        self.downloader = None
        self.pool = None
        self.is_downloading = False
        self.file_being_downloaded = None
        self.index_of_song_being_downloaded = 0
        self.number_of_available_videos = 0

        # Player
        self.is_watching = False
        self.is_playing = False
        self.video_being_played = None
        self.index_of_song_being_watched = 0
        self.length = None
        self.gauge_bar_offset = 0

        self.directory = utils.make_directory(directory)

        self.build_UI()
        self.Show()
        self.panel.Layout()
        # self.Maximize()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(100)

    def build_UI(self):
        self.CreateStatusBar()
        self.create_menu()
        self.create_player_and_buttons()

    def create_menu(self):
        filemenu = wx.Menu()

        menuOpen = filemenu.Append(wx.NewId(), "&Open", "Open a file")
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", "Information about this program!")
        menuExit = filemenu.Append(wx.ID_EXIT, "&Exit", "Exit this program")

        self.Bind(wx.EVT_MENU, self.on_open, menuOpen)
        self.Bind(wx.EVT_MENU, self.on_about, menuAbout)
        self.Bind(wx.EVT_MENU, self.on_exit, menuExit)

        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&File")
        self.SetMenuBar(menuBar)

    def create_player_and_buttons(self):
        self.panel = wx.Panel(parent=self)

        # Make sizer
        outerBoxSizer = wx.BoxSizer(wx.VERTICAL)
        searchInputSizer = self.create_search_input_sizer()
        gaugeBarSizer = self.make_gauge_bar_sizer()
        playerButtonsSizer = self.make_player_button_sizer()

        # Add player and events
        mplayer_controller = mpc.MplayerCtrl(self.panel, -1, 'mplayer')
        self.media_player = MediaPlayer(mplayer_controller)
        self.bind_events_to_media_player()

        # Add sizer to outer sizer
        outerBoxSizer.Add(searchInputSizer, 0, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(mplayer_controller, 1, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(gaugeBarSizer, 0, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(playerButtonsSizer, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        self.panel.SetSizer(outerBoxSizer)

    def bind_events_to_media_player(self):
        self.panel.Bind(mpc.EVT_MEDIA_STARTED, self.on_media_started)
        self.panel.Bind(mpc.EVT_MEDIA_FINISHED, self.on_media_finished)

    def make_gauge_bar_sizer(self):
        self.gauge_bar = wx.Gauge(self.panel, style=2)

        gauge_bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        gauge_bar_sizer.Add(self.gauge_bar, proportion=1, flag=wx.ALL, border=5)
        return gauge_bar_sizer

    def make_player_button_sizer(self):
        """
        Creates all the buttons for the player: previous, play, pause, reset and next.
        """
        player_flow_sizer = wx.BoxSizer(wx.HORIZONTAL)

        data_list = [{'label': 'Previous', 'handler': self.on_previous},
                     {'label': 'Play', 'handler': self.on_play},
                     {'label': 'Pause', 'handler': self.on_pause},
                     {'label': 'Reset', 'handler': self.on_reset},
                     {'label': 'Next', 'handler': self.on_next}]

        for button_properties in data_list:
            button = self.make_button(button_properties)
            player_flow_sizer.Add(button, 0, wx.ALL, 3)

        return player_flow_sizer

    def make_button(self, button_properties):
        button = wx.Button(self.panel, label=button_properties['label'])

        button.SetInitialSize()
        button.Bind(wx.EVT_BUTTON, button_properties['handler'])

        return button

    def create_search_input_sizer(self):
        self.search_terms_input = wx.TextCtrl(self.panel)
        search_button = wx.Button(self.panel, label='Watch')
        self.Bind(wx.EVT_BUTTON, self.on_search, search_button)

        # todo: currently doesn't work. Pressing a key has no effect
        # todo: also we must do this only for the return key, not just any key pressed
        # todo: becayse otherwise we simply would search at every keystroke
        # self.Bind(wx.EVT_KEY_DOWN, self.on_search, self.search_terms_input)

        # Add controls to sizer
        search_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_box_sizer.Add(self.search_terms_input, proportion=1, flag=wx.ALL, border=10)
        search_box_sizer.Add(search_button, 0, flag=wx.ALL, border=8)

        return search_box_sizer

    def update_gauge(self):
        if self.is_video_playing():
            self.gauge_bar_offset = self.get_current_length()
            self.gauge_bar.SetValue(self.gauge_bar_offset)







    # -------- Event Handlers ---------------------------------

    def on_open(self, evt):
        dialog = wx.FileDialog(self, message="Choose a file",
                               defaultDir=os.getcwd(),
                               defaultFile="",
                               wildcard="*.*",
                               style=wx.OPEN | wx.CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.play_file(path)

        dialog.Destroy()

    def on_about(self, evt):
        dialog = wx.MessageDialog(self, "A video streaming service",
                                  "About streaming service", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def on_media_started(self, evt):
        self.is_playing = True
        self.gauge_bar_offset = 0
        self.length = self.downloader.get_current_video_length()
        self.gauge_bar.SetRange(self.length)
        print("Length of file: %d" % self.length)

    def on_media_finished(self, evt):
        self.is_playing = False
        self.length = float('infinity')

    def on_exit(self, evt):
        self.downloader.destroy()
        self.Close(True)

    def on_previous(self, evt):
        if self.current_song_index != 0:
            self.start_downloading_if_needed(self.current_song_index - 1)
            self.play_current_song_when_big_enough()

    def on_pause(self, evt):
        self.media_player.pause()

    def on_play(self, evt):
        self.media_player.unpause()

    def on_reset(self, evt):
        self.media_player.reset()

    def on_next(self, evt):
        self.start_downloading_if_needed(self.current_song_index + 1)
        self.play_current_song_when_big_enough()

    def on_timer(self, evt):
        pass

    def on_search(self, evt):
        search_terms = self.get_search_terms()
        self.downloader = self.build_downloader(search_terms)
        self.download_first_video()
        self.play_current_song_when_big_enough()

    def is_video_playing(self):
        return self.is_playing

    def get_current_length(self):
        return 0

    def play_file(self, path):
        try:
            self.start_playing_file(path)
        except IndexError as e:
            self.raise_error_window(path)
            print (e.message)

    def start_playing_file(self, path):
        print("Playing: ", path)
        #if not self.mediaPlayer:
        # todo: don't forget to see what this line was for
        # todo: make notes about decisions
        # self.mediaPlayer.Quit()
        #self.mediaPlayer.Start()
        self.media_player.play_file(path)
        #if loop:
        #   self.mediaPlayer.Loop(0)

        self.video_being_played = path
        self.playing = True

    def raise_error_window(self, path):
        message = "Unable to load %s: Unsupported format?" % path
        wx.MessageBox(message, "ERROR", wx.ICON_ERROR | wx.OK)

app = wx.App(False)
frame = Player()
app.MainLoop()

#todo: on watch also
