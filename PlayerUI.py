# coding=utf-8
import os
import wx

import MplayerCtrl as mpc
from MediaPlayer import MediaPlayer
from PlayerManager import PlayerManager
import utils

BIG_VALUE = 10 ** 8

TIMER_INTERVAL = 0.1

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 800


class PlayerUI(wx.Frame):
    def __init__(self, directory=None):
        super(PlayerUI, self).__init__(parent=None, title="YouStream",
                                       size=(DEFAULT_WIDTH, DEFAULT_HEIGHT))

        self.directory = utils.make_directory(directory)

        self.build_UI()
        self.Show()
        self.panel.Layout()
        # self.Maximize()

        self.player_manager = PlayerManager(self.media_player, self.directory)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(TIMER_INTERVAL * 1000)

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


    # -------- Event Handlers ---------------------------------

    def on_open(self, evt):
        dialog = wx.FileDialog(self, message="Choose a file",
                               defaultDir=os.getcwd(),
                               defaultFile="",
                               wildcard="*.*",
                               style=wx.OPEN | wx.CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.player_manager.open(path)

        dialog.Destroy()

    def on_about(self, evt):
        dialog = wx.MessageDialog(self, "A video streaming service",
                                  "About streaming service", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def on_media_started(self, evt):
        self.update_gauge()
        self.player_manager.on_media_started()
        length = self.player_manager.get_current_video_length()
        print("Length of file: %d" % length)

    def on_media_finished(self, evt):
        self.set_gauge_bar_empty()
        self.player_manager.on_media_finished()

    def on_exit(self, evt):
        self.media_player.destroy()
        self.player_manager.destroy()
        self.Close(True)

    def on_previous(self, evt):
        self.player_manager.on_previous()

    def on_pause(self, evt):
        self.player_manager.on_pause()

    def on_play(self, evt):
        self.player_manager.on_play()

    def on_reset(self, evt):
        self.player_manager.on_reset()

    def on_next(self, evt):
        self.player_manager.on_next()

    def on_search(self, evt):
        search_terms = self.get_search_terms()
        self.player_manager.on_search(search_terms)

    def on_timer(self, evt):
        # todo: if, for some reason (SLOW internet), the media player goes to the end of the file
        # todo: it will stop and dont try to continue when new contents are ready. Fix this!

        must_restart_video = self.must_restart_video()
        if must_restart_video:
            print "Restarting video."
            self.restart_video()

        if self.player_manager.is_video_playing():
            self.video_time_position = self.player_manager.get_current_video_time_position()
            self.update_gauge()

        self.player_manager.on_timer()




    # Helper function

    def get_search_terms(self):
        return self.search_terms_input.GetValue().split()

    def restart_video(self):
        path = self.player_manager.get_current_video_file_path()
        video_time_position = self.player_manager.get_current_video_time_position()
        self.media_player.play_current_video_at_time_position(path, video_time_position)

    def must_restart_video(self):
        is_downloading = self.player_manager.is_downloading()
        is_video_playing = self.player_manager.is_video_playing()
        current_time_position = self.player_manager.get_current_video_time_position()

        return not is_video_playing and is_downloading and current_time_position > 2

    def raise_error_window(self, path):
        message = "Unable to load %s: Unsupported format?" % path
        wx.MessageBox(message, "ERROR", wx.ICON_ERROR | wx.OK)








    # Gauge

    def update_gauge(self):
        if self.player_manager.is_video_playing():
            self.adjust_gauge()

    def adjust_gauge(self):
        if self.must_adjust_gauge():
            self.adjust_gauge_range()

        self.adjust_gauge_value()

    def must_adjust_gauge(self):
        return self.gauge_bar.GetRange() == 0 or self.gauge_bar.GetRange() == BIG_VALUE

    def adjust_gauge_range(self):
        length = self.player_manager.get_current_video_length()

        if length == 0:
            self.set_gauge_bar_empty()
        else:
            self.gauge_bar.SetRange(length)

    def set_gauge_bar_empty(self):
        self.gauge_bar.SetRange(BIG_VALUE)
        self.gauge_bar.SetValue(0)

    def adjust_gauge_value(self):
        video_time_position = self.player_manager.get_current_video_time_position()
        self.gauge_bar.SetValue(video_time_position)


app = wx.App(False)
frame = PlayerUI()
app.MainLoop()