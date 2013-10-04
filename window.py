# coding=utf-8
import os
import wx
from multiprocessing.pool import ThreadPool
import time

import MplayerCtrl as mpc

from downloader import Downloader


DEFAULT_WIDTH = 1000
DEFAULT_HEIGHT = 1000


class MainWindow(wx.Frame):
    def __init__(self, directory=None):
        super(MainWindow, self).__init__(parent=None, title="YouStream",
                                         size=(DEFAULT_WIDTH, DEFAULT_HEIGHT))
        self.downloader = None
        self.pool = None
        self.current_func_pool = None
        self.is_downloading = False
        self.file_being_downloaded = None
        self.index_of_song_being_downloaded = 0

        self.is_watching = False
        self.playing = False
        self.paused = True
        self.video_being_played = None
        self.index_of_song_being_watched = 0
        self.length = None

        self.gauge_bar_offset = 0
        self.number_of_songs_predownloaded = 0
        self.directory = self.get_directory_and_build_it_if_necessary(directory)

        self.init_UI()

        self.Show()
        self.panel.Layout()
        self.Maximize()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        self.timer.Start(100)

    # -------- UI, sizers and widgets ---------------------------
    def init_UI(self):
        """
        Creates the menu, the status bar and the controls for the player (play, pause, ...)
        @return: None
        """
        self.create_menu_and_status_bar()
        self.create_panel_and_buttons()

    def create_menu_and_status_bar(self):
        """
        Builds the status bar and the menu bar.
        @return: None
        """
        self.CreateStatusBar()
        self.create_menu()

    def create_panel_and_buttons(self):
        """
        Creates the panel and the controls for the player (play, pause, ...)
        @return: None
        """
        self.panel = wx.Panel(parent=self)

        # Make sizer
        outerBoxSizer = wx.BoxSizer(wx.VERTICAL)
        searchInputSizer = self.create_search_input_sizer()
        gaugeBarSizer = self.create_gauge_bar_sizer()
        playerButtonsSizer = self.create_player_button_sizer()

        # Add player and events
        self.mediaPlayer = mpc.MplayerCtrl(self.panel, -1, 'mplayer')

        self.panel.Bind(mpc.EVT_MEDIA_STARTED, self.on_media_started)
        self.panel.Bind(mpc.EVT_MEDIA_FINISHED, self.on_media_finished)
        self.panel.Bind(mpc.EVT_PROCESS_STARTED, self.on_process_started)
        self.panel.Bind(mpc.EVT_PROCESS_STOPPED, self.on_process_stopped)

        # Add sizer to outer sizer
        outerBoxSizer.Add(searchInputSizer, 0, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(self.mediaPlayer, 1, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(gaugeBarSizer, 0, wx.ALL | wx.EXPAND, 5)
        outerBoxSizer.Add(playerButtonsSizer, 0, wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        self.panel.SetSizer(outerBoxSizer)

    def on_media_started(self, evt):
        """
        When a file is loaded (media_started_evt), this will set the appropriate flags
        and set the gauge bar to the correct length.
        @param evt: The event return by wx
        @return: None
        """
        print("media_started")
        self.playing = True
        self.gauge_bar_offset = 0
        self.length = self.downloader.get_length(self.index_of_song_being_watched)
        print("Length of file: ", self.length)
        self.gauge_bar.SetRange(self.length)

    def on_media_finished(self, evt):
        """
        When a file ends (media_finished_evt), this will set the appropriate flags
        and set the gauge bar to the correct length (infinity).
        @param evt: The event return by wx
        @return: None
        """
        print("media_finished")
        self.playing = False
        self.length = float('infinity')

    def on_process_started(self, evt):
        print("process_started")

    def on_process_stopped(self, evt):
        print("process_stopped")

    def create_gauge_bar_sizer(self):
        """
        Creates the gauge bar.
        @return: None
        """
        gauge_bar_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.gauge_bar = wx.Gauge(self.panel, style=2)
        gauge_bar_sizer.Add(self.gauge_bar, proportion=1, flag=wx.ALL, border=5)
        return gauge_bar_sizer

    def create_player_button_sizer(self):
        """
        Creates all the buttons for the player: previous, play, pause, reset and next.
        @return: the player flow sizer
        """
        player_flow_sizer = wx.BoxSizer(wx.HORIZONTAL)

        data_list = [{ 'label': 'Previous', 'handler': self.on_previous },
                     { 'label': 'Play', 'handler': self.on_play },
                     { 'label': 'Pause', 'handler': self.on_pause },
                     { 'label': 'Reset', 'handler': self.on_reset },
                     { 'label': 'Next', 'handler': self.on_next }]

        for button_properties in data_list:
            self.build_button(button_properties, player_flow_sizer)

        return player_flow_sizer

    def build_button(self, button_properties, player_flow_sizer):
        """
        Builds a button from the given properties and inserts it into the sizer.
        @param button_properties: The button properties
        @param player_flow_sizer: The overall player flow sizer
        @return: None
        """
        button = wx.Button(self.panel, label=button_properties['label'])

        button.SetInitialSize()
        button.Bind(wx.EVT_BUTTON, button_properties['handler'])

        player_flow_sizer.Add(button, 0, wx.ALL, 3)

    def create_search_input_sizer(self):
        """
        Makes the input and button necessary for search, and then inserts them into the sizer.
        @return: the search box sizer
        """
        search_box_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search_terms_input = wx.TextCtrl(self.panel)
        search_button = wx.Button(self.panel, label='Watch')
        self.Bind(wx.EVT_BUTTON, self.on_search, search_button)

        # todo: currently doesn't work. Pressing a key has no effect
        # todo: also we must do this only for the return key, not just any key pressed
        # todo: becayse otherwise we simply would search at every keystroke
        self.Bind(wx.EVT_KEY_DOWN, self.on_search, self.search_terms_input)

        # Add controls to sizer
        search_box_sizer.Add(self.search_terms_input, proportion=1, flag=wx.ALL, border=10)
        search_box_sizer.Add(search_button, 0, flag=wx.ALL, border=8)

        return search_box_sizer

    def create_menu(self):
        """
        Creates the menu bar, builds the file menus and sets it.
        @return:
        """
        filemenu = wx.Menu()

        # Set various menu options
        menuOpen = filemenu.Append(wx.NewId(), "&Open", "Open a file")
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", "Information about this program!")
        menuExit = filemenu.Append(wx.ID_EXIT, "&Exit", "Exit this program")

        # Set events
        self.Bind(wx.EVT_MENU, self.on_open, menuOpen)
        self.Bind(wx.EVT_MENU, self.on_about, menuAbout)
        self.Bind(wx.EVT_MENU, self.on_exit, menuExit)

        # Create menu bar and attach menu to it
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&File")
        self.SetMenuBar(menuBar)

    def update_gauge(self):
        """
        If the player is on and we have the length of the current file, we try to
        update the gauge bar. If we can't access the position in the file or the
        length of the video, we default to 0.
        @return: None
        """
        if self.playing and self.length:
            try:
                self.gauge_bar_offset = self.mediaPlayer.time_pos
            except AttributeError:
                # Hack when media player doesnt work (ALWAYS !!!!!) The value is 0.1s because that is the timer offset
                self.gauge_bar_offset += 0.1

        if type(self.gauge_bar_offset) != int and type(self.gauge_bar_offset) != float:
            self.gauge_bar_offset = 0

        self.gauge_bar.SetValue(int(self.gauge_bar_offset))


    # ------------- Download -------------------------------------

    def start_downloader(self, searchTermsTokens):
        """
        Given the search tokens, start a downloader and download the first song.
        Also sets the appropriate flags.
        @param searchTermsTokens:
        @return: None
        """
        self.downloader = Downloader(searchTermsTokens, self.directory)
        self.index_of_song_being_downloaded = 0
        self.index_of_song_being_watched = 0

    def is_song_already_downloaded(self, index):
        """
        @param index: index of the song.
        @return: true if the song has already been downloaded, else returns false.
        """
        # In case this line is triggered before the download started, we check that it is not None
        # This can be the case because the download is asynchronous and takes
        # some time to start
        return self.downloader and self.downloader.is_song_already_downloaded(index)

    def fetch_next_song(self):
        """
        Starts downloading the song after the current one.
        @return: None
        """
        self.download_song(self.index_of_song_being_downloaded + 1)

    def download_song(self, index):
        """
        Downloads next song through the downloader and set the appropriate flags.
        Note: downloads at lower speed the next video if there the next son is ready.
        @param index: the index of the song
        @return: None
        """
        is_prefetching = (self.number_of_songs_predownloaded != 0)
        self.number_of_songs_predownloaded += 1
        self.is_downloading = True
        self.index_of_song_being_downloaded = index
        self.downloader.download_song(index, is_prefetching)
        self.file_being_downloaded = self.downloader.get_downloading_video_path()

    # ------------- Watch ----------------------------------------

    def move_and_play_song(self, change):
        """
        Watches the song whose index is (the current index + change).
        If that song isn't already downloaded, stops the current download and begins a new one.
        @param change: the change to the current song index
        @return: None
        """
        print("Video being downloaded: ", self.downloader.get_downloading_video_path())
        print("Video being played:", self.video_being_played)
        # Will be needed when move more than by 1
        self.run_function_assychronously(self.download_if_needed_wait_and_watch_video,
                                         self.index_of_song_being_watched + change)

    def download_if_needed_wait_and_watch_video(self, index):
        """
                If the video is not downloaded yet and we aren't downloading it, begin the download.
                Then set the index to the correct value and watch the new video.
                @param index: the new index of the current song
                @return: None
                """
        # todo: set screen to a loading wheel gif, so that the user know the file is loading
        # todo: problem -> media player doesn't loop. Setting mpc.Loop(0) has no effect
        # todo: maybe must try different format. Possible problem: file is a GIF. Try avi or mp4.
        # Completed  ->  todo: if song was downloaded, try prefetching song after it
        LOADING_GIF_FILE = os.getcwd() + '/loading.gif'
        print(LOADING_GIF_FILE)
        #self.load_file(LOADING_GIF_FILE, loop=True)
        if not self.is_song_already_downloaded(index) and self.index_of_song_being_downloaded != index:
            print("Didn't download song yet. Index: ", index)
            self.downloader.skip_download_of_song()
            self.download_song(index)
        else:
            print("Hello")
            self.try_prefetching_next_song(index)

        self.index_of_song_being_watched = index
        self.wait_while_file_is_small_and_watch_song_being_downloaded()

    def try_prefetching_next_song(self, index):
        """
        Given an index, tries to prefetch the songs after it. To do this, it search each one
        in ascending order. When it stumbles on an undownloaded song, it begins to download that one.
        If the downloader was already downloading one of these songs, it does nothing
        @param index:
        """
        NUM_SONGS = 2
        if index < self.index_of_song_being_downloaded < index + NUM_SONGS:
            return

        self.downloader.skip_download_of_song()
        for song_to_download_index in range(index, index + NUM_SONGS + 1):
            if not self.downloader.is_song_already_downloaded(song_to_download_index):
                self.downloader.skip_download_of_song()
                self.download_song(song_to_download_index)
                return


    def wait_while_file_is_small_and_watch_song_being_downloaded(self):
        """
        Sets the appropriate flags and gets the filepath from the song being downloaded.
        Then starts an asynchronous thread. This thread will wait while the file is small
        and then start playing it.
        @return: None
        """
        index = self.index_of_song_being_watched
        path = self.downloader.get_file_path(index)
        self.playing = True
        self.paused = False
        self.pool = ThreadPool(processes=1)
        self.pool.apply_async(self.wait_while_small_then_play_song, args=(path, ))
        self.pool.close()

    def wait_while_small_then_play_song(self, path):
        """
        Waits while the file size is below 1.5 MB, then loads the file.
        After that sets the gauge bar back to the beginning.
        @param path: the path of the file
        @return: None
        """
        MIN_FILE_SIZE = 1.5 * 1024 * 1024

        self.number_of_songs_predownloaded -= 1
        if not self.downloader.is_song_already_downloaded(self.index_of_song_being_watched):
            self.downloader.wait_while_file_is_small(path, MIN_FILE_SIZE)
            print("File is big enough to play. Size:", os.path.getsize(path))
        self.load_file(path)
        self.gauge_bar_offset = 0

    def load_file(self, path, loop=False):
        """
        Tries to load the file in the media player (quits current m.p., starts a new one
        and loads the file from the path). If there is an error, build an error message box.
        @param path: the path of the file.
        @param loop: the looping flag.
        @return: None
        """
        path = str(path)
        try:
            print("Playing: ", path)
            if not self.mediaPlayer:
                # todo: don't forget to see what this line was for
                # todo: make notes about decisions
                # self.mediaPlayer.Quit()
                self.mediaPlayer.Start()
            self.mediaPlayer.Loadfile(path)
            if loop:
                self.mediaPlayer.Loop(0)

            self.video_being_played = path
            self.playing = True
        except IndexError as e:
            print(e)
            message = "Unable to load %s: Unsupported format?" % path
            wx.MessageBox(message, "ERROR", wx.ICON_ERROR | wx.OK)


    # -------- Event Handlers ---------------------------------

    def on_open(self, evt):
        """
        This is the event handler for the open file option in the menu bar.
        It launches a select file dialog, and then tries to load that file in
        the media player.
        @param evt: the event
        @return: None
        """
        dialog = wx.FileDialog(self, message="Choose a file",
                               defaultDir=os.getcwd(),
                               defaultFile="",
                               wildcard="*.*",
                               style=wx.OPEN | wx.CHANGE_DIR)

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.load_file(path)
        dialog.Destroy()

    def on_about(self, evt):
        """
        Event handler for the about file menu in the menu bar. It pops up a window
        about the current player.
        @param evt: the about event
        @return: None
        """
        dialog = wx.MessageDialog(self, "A video streaming service",
                                  "About streaming service", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def start_with_new_search_terms(self):
        searchTerms = self.search_terms_input.GetValue()
        searchTermsTokens = searchTerms.split()
        if self.is_watching:
            self.downloader.skip_download_of_song()
            self.playing = False
            self.video_being_played = None
            self.number_of_songs_predownloaded = 0
            self.is_downloading = False
            self.length = None
            print("Stopping current download.")
        print("Starting next download.")
        self.start_downloader(searchTermsTokens)
        print("Started downloading next song.")
        self.download_if_needed_wait_and_watch_video(index=0)
        self.is_watching = True
        print("Started to watch the next song.")
        time.sleep(2)

    def on_search(self, evt):
        # Todo: search if event is press on button or keypress on the return key
        """
        This is the event handler for the search box. When a request is made,
        if find the search tokens. Then, if the media player is started (not necessarily on play),
        it stops the current media player and sets the appropriate flags.
        Note: It sleeps for two seconds. Why??? I don't know.
        @param evt: the event
        @return: None
        """
        self.run_function_assychronously(self.start_with_new_search_terms)

    # todo: make buttons usable immediately, that is, do action on asynchronous thread
    # todo: for 'next' button

    def on_play(self, evt):
        """
        Event handler for the play button. Un-pauses the player if it's
        current paused.
        @param evt: the event
        @return: None
        """
        print("Play")

        if self.paused:
            self.mediaPlayer.Pause()  # Strangely, this method toggles the pause attribute (bad name)
        self.paused = False

    def on_pause(self, evt):
        """
        Event handler for the stop button. Pauses the player if it's
        current playing.
        @param evt: the event
        @return: None
        """
        print("Stop")
        if not self.paused:
            self.mediaPlayer.Pause()
        self.paused = True

    def on_reset(self, evt):
        """
        Event handler for the reset button. Resets the video to the beginning.
        Sets the gauge bar to the beginning.
        @param evt: the event
        @return: None
        """
        self.mediaPlayer.Seek(0, type_=1)
        self.gauge_bar.SetValue(0)

    def on_next(self, evt):
        """
        Event handler for the next button. If needed, stops the current download and begins a new one.
        @param evt: the event
        @return: None
        """
        self.move_and_play_song(1)

    def on_previous(self, evt):
        """
        Event handler for the previous button. If needed, stops the current download and begins a new one.
        Note: no effect when the current song is the first one.
        @param evt: the event
        @return: None
        """
        if self.index_of_song_being_watched != 0:
            self.move_and_play_song(-1)

    def on_timer(self, evt):
        """
        Event handler for the timer event. This function is set to work every 100 ms.
        It does all the book keeping and updating necessary for the application. It's the epicenter
        of the application when it is started.

        When playing, it updates the gauge bar. Then, if a download ended, it begins to fetch the next song.
        If the song ended, starts downloading it if necessary (shouldn't need to) and playing that song.
        @param evt: the timer event.

        If the length of the file is undefined, try to get it.
        @return: None
        """
        if not self.paused:
            self.update_gauge()

        # In case this line is triggered before the download started, we check that it is not None
        # This can be the case because the download is asynchronous and takes
        # some time to start
        self.is_downloading = self.is_watching and self.downloader and self.downloader.is_downloading()

        # If download stopped and we were not playing the video, mark it as ready for later use
        if self.is_watching:

            if self.downloader and not self.is_downloading and self.number_of_songs_predownloaded <= 2:
                print("Downloading next song")
                self.fetch_next_song()

            if self.is_watching and not self.playing and self.downloader:
                print("Watching next song")
                self.download_if_needed_wait_and_watch_video(self.index_of_song_being_watched + 1)

    def on_exit(self, evt):
        """
        Event handler for the exit event. Stops the download and closes the UI.
        @param evt:
        @return:
        """
        self.downloader.skip_download_of_song()
        self.Close(True)

    # -------- Miscellaneous stuff ---------------------------

    def get_directory_and_build_it_if_necessary(self, default_directory):
        """
        Sets the directory for the songs. If it doesn't exists, it creates it.
        @param default_directory: the default directory path_
        @return: the directory
        """
        directory = default_directory
        if directory is None:
            directory = os.getcwd() + '/songs/'

        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def run_function_assychronously(self, function, *args, **kwargs):
        print(args, kwargs)
        self.try_to_terminate_previous_pool()
        self.current_func_pool = ThreadPool(processes=1)
        self.current_func_pool.apply_async(function, args, kwargs)

    def try_to_terminate_previous_pool(self):
        if self.current_func_pool:
            self.current_func_pool.terminate()
        self.current_func_pool = None


app = wx.App(False)
frame = MainWindow()
app.MainLoop()

#todo: on watch also
