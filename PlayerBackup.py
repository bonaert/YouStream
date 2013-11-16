import wx
import os
import time

from multiprocessing.pool import ThreadPool
from Downloader import Downloader

# ------------- Download -------------------------------------
    def start_downloader(self, searchTermsTokens):
        self.downloader = Downloader(searchTermsTokens, self.directory)
        self.index_of_song_being_downloaded = 0
        self.index_of_song_being_watched = 0

    def fetch_next_song(self):
        self.download_song(self.index_of_song_being_downloaded + 1)

    def download_song(self, index):
        self.set_prefetching_if_wanted()
        self.downloader.download_video_with_index(index)
        self.update_fields_after_download_started(index)

    def update_fields_after_download_started(self, index):
        self.number_of_available_videos += 1
        self.is_downloading = True
        self.index_of_song_being_downloaded = index
        self.file_being_downloaded = self.downloader.get_current_video_file_path()

    def set_prefetching_if_wanted(self):
        must_prefetch = self.number_of_available_videos != 0
        if must_prefetch:
            self.downloader.set_prefetching_download_speed()
        else:
            self.downloader.set_full_download_speed()


    # ------------- Watch ----------------------------------------
    def move_and_play_song(self, change):
        """
        Watches the song whose index is (the current index + change).
        If that song isn't already downloaded, stops the current download and begins a new one.
        @param change: the change to the current song index
        @return: None
        """
        print("Video being downloaded: ", self.downloader.get_current_video_file_path())
        print("Video being played:", self.video_being_played)
        # Will be needed when move more than by 1
        self.run_function_asynchronously(self.download_if_needed_wait_and_watch_video,
                                         self.index_of_song_being_watched + change)

    def set_loading_gif_in_player(self):
        LOADING_GIF_FILE = os.getcwd() + '/loading.gif'
        #print(LOADING_GIF_FILE)
        #self.load_file(LOADING_GIF_FILE, loop=True)

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
        self.set_loading_gif_in_player()

        must_download_song = not self.is_song_already_downloaded(index) and not self.is_song_being_downloaded(index)
        if must_download_song:
            print "Didn't download song yet. Index: %d" % index
            self.downloader.stop_download()
            self.download_song(index)
        else:
            print "Prefetching song with index %d" % index
            self.try_prefetching_next_song(index)

        self.index_of_song_being_watched = index
        self.wait_while_file_is_small_and_watch_song_being_downloaded()
        print ("GNOE")

    def is_song_already_downloaded(self, index):
        return self.downloader and self.downloader.is_video_already_downloaded(index)

    def is_song_being_downloaded(self, index):
        return self.downloader and self.downloader.is_video_downloading(index)

    def index_of_song_being_downloaded(self):
        return self.downloader.get_current_video_index()

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

        self.downloader.stop_download()
        for song_to_download_index in range(index, index + NUM_SONGS + 1):
            if not self.downloader.is_video_already_downloaded(song_to_download_index):
                self.downloader.stop_download()
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
        print("Getting path")
        path = self.downloader.get_file_path_of_video_with_index(index)
        print(path)
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
        print("A")

        self.number_of_available_videos -= 1
        if not self.downloader.is_video_already_downloaded(self.index_of_song_being_watched):
            self.wait_while_file_is_small(self.index_of_song_being_watched, MIN_FILE_SIZE)
            print("File is big enough to play. Size:", os.path.getsize(path))
        self.load_file(path)
        self.gauge_bar_offset = 0

    def wait_while_file_is_small(self, index, size):
        self.downloader.wait_while_video_is_small(index, size)

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


    def start_with_new_search_terms(self):
        searchTerms = self.search_terms_input.GetValue()
        searchTermsTokens = searchTerms.split()

        if self.is_watching:
            self.downloader.destroy()
            self.update_field_after_creating_new_downloader()

        print("Starting downloader with terms %s." % ''.join(searchTermsTokens))
        self.start_downloader(searchTermsTokens)
        print("Started downloading next song.")
        self.download_if_needed_wait_and_watch_video(index=0)
        print("Started to watch the next song.")
        self.is_watching = True
        time.sleep(2)

    def update_field_after_creating_new_downloader(self):
        self.playing = False
        self.video_being_played = None
        self.number_of_available_videos = 0
        self.is_downloading = False
        self.length = None

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
        self.run_function_asynchronously(self.start_with_new_search_terms)

    # todo: make buttons usable immediately, that is, do action on asynchronous thread
    # todo: for 'next' button

    def on_play(self, evt):
        print("Play")

        if self.paused:
            self.mediaPlayer.Pause()  # Strangely, this method toggles the pause attribute (bad name)
        self.paused = False

    def on_pause(self, evt):
        print("Stop")
        if not self.paused:
            self.mediaPlayer.Pause()
        self.paused = True

    def on_reset(self, evt):
        self.mediaPlayer.Seek(0, type_=1)
        self.gauge_bar.SetValue(0)

    def on_next(self, evt):
        self.move_and_play_song(1)

    def on_previous(self, evt):
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

            if self.downloader and not self.is_downloading and self.number_of_available_videos <= 2:
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
        self.downloader.stop_download()
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

    def run_function_asynchronously(self, function, *args, **kwargs):
        print(args, kwargs)
        self.try_to_terminate_previous_pool()
        self.current_func_pool = ThreadPool(processes=1)
        self.current_func_pool.apply_async(function, args, kwargs)

    def try_to_terminate_previous_pool(self):
        if self.current_func_pool:
            self.current_func_pool.terminate()
        self.current_func_pool = None