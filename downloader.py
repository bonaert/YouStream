# coding=utf-8
import os
import string
import subprocess
import time
from multiprocessing.pool import ThreadPool

import utils


class Downloader(object):
    """
    A downloader, will, given some search terms and a directory to store the files,
    provide methods to download songs. It allows you to skip videos, to filter them,
    to get various information about the videos and other useful methods.
    @param search_terms: the search tokens
    @param directory: the directory to store the files
    """

    def __init__(self, search_terms, directory):
        self.search_terms = search_terms
        self.songs_metadata = utils.get_songs_metadata(search_terms)
        self.directory = directory

        self.current_song_index = 0
        self.is_downloading_now = False
        self.max_download_rate = 200
        self.path_of_video_being_downloaded = None
        self.last_video_finished_filepath = None

        self.downloaded_songs_indices = set()
        self.downloaded_songs_paths = {}

        self.pool = None
        self.download_subprocess = None

        # Since we have already the first 10
        self.index_of_next_songs_to_download = 11

    def get_next_10_songs_metadata(self):
        metadata = utils.get_songs_metadata(self.search_terms, self.index_of_next_songs_to_download)
        self.index_of_next_songs_to_download += 10
        return metadata

    def add_next_10_songs_metadata(self):
        new_metadata = self.get_next_10_songs_metadata()
        self.songs_metadata.extend(new_metadata)

    def need_to_get_metadata(self):
        return len(self.songs_metadata) > self.current_song_index and \
            'url' in self.songs_metadata[self.current_song_index]

    def is_next_song_to_download(self):
        return not self.need_to_get_metadata()

    def get_current_song_url(self):
        return self.songs_metadata[self.current_song_index]['url']

    def get_song_url(self):
        if self.is_next_song_to_download():
            return self.get_current_song_url()
        else:
            return None

    def get_next_song_url(self):
        """
        @return: The url of the next song. (None if none can be found)
        """
        if self.need_to_get_metadata():
            self.add_next_10_songs_metadata()

        return self.get_song_url()

    def download_song(self, index, is_prefetching=False):
        #todo: return signal if no extra song can be downloaded
        """
        Starts downloading the song with the given index. If prefetching, will downloaded
        at lower download rate. If there are no more song, returns and does nothing.
        @param index: the index of the song to download.
        @param is_prefetching: the prefetching flag
        @return: None
        """
        self.current_song_index = index
        url = self.get_next_song_url()
        print("Got url:", url)

        if url is None:
            print("No more songs")
            return

        title = self.get_title(url)

        try:
            print("Title:", title)
            self.start_downloading(url, index, is_prefetching)
            print("Getting path")
            self.path_of_video_being_downloaded = self.get_song_path_from_title(title)
            print("Got path:", self.path_of_video_being_downloaded)
        except (OSError, IOError):
            self.skip_download_of_song()

    def start_downloading(self, url, index, is_prefetching=False):
        """
        Start a asynchronous thread to download the next song and set the appropriate flags.
        @param url: the url of the song.
        @param index: the index of the song.
        @param is_prefetching: the prefetching flag.
        @return: None
        """
        self.is_downloading_now = True
        self.pool = ThreadPool(processes=1)
        self.pool.apply_async(self.download_wait_until_end_and_quit, args=(url, index, is_prefetching))
        self.pool.close()

    def wait_while_file_is_small(self, path, size):
        """
        Waits while the file is smaller than the provided size. If the download ended, then also return
        to prevent edge cases when to file to download is smaller than the provided size. (Ex: We want to wait
        while file size is at least 2 MB but the complete file is only 1.2 MB)
        @param path: the path of the file
        @param size: the minimum size
        @return: None
        """
        # todo: if file is smaller that minimum size, must also return when it ended
        while self.is_downloading_now and (not os.path.exists(path) or os.path.getsize(path) < size):
            time.sleep(0.3)
            print("Too small")

    def get_title(self, url):
        """
        Return the title of the song at the provided url.
        @param url: the url of the song.
        @return: the title of the song.
        """
        # todo: there is discrepancy between title returned by this process
        # todo: and the title written on disk. Must find out why
        title = subprocess.check_output(['youtube-dl', '-e', url])
        return title.strip()

    def skip_download_of_song(self):
        """
        Skips the download of the current song. First, tries to terminate the subprocess.
        Then terminates the thread pool and sets the appropriate flag.
        Sleeps for 1 second. Why ????  I don't know
        @return: None
        """
        if self.download_subprocess and self.download_subprocess.poll() is None:
            self.download_subprocess.terminate()

        if self.pool:
            self.pool.terminate()

        self.is_downloading_now = False
        self.download_subprocess = None
        self.pool = None
        self.path_of_video_being_downloaded = None
        time.sleep(1)

    def download_wait_until_end_and_quit(self, url, index, is_prefetching=False):
        """
        Starts the download subprocess and waits until it finishes. Then it add it to the
        downloaded songs set and sets the appropriate flags.
        @param url:
        @param index:
        @param is_prefetching:
        @return:
        """
        print("Download started")
        self.start_download_subprocess(url, is_prefetching)
        print("Waiting")
        self.download_subprocess.wait()
        print("Download ended")

        # If song was not already downloaded
        if self.path_of_video_being_downloaded[-5:] == '.part':
            self.last_video_finished_filepath = self.path_of_video_being_downloaded[:-5]
        else:
            self.last_video_finished_filepath = self.path_of_video_being_downloaded

        self.downloaded_songs_indices.add(index)
        self.downloaded_songs_paths[index] = self.path_of_video_being_downloaded
        self.is_downloading_now = False
        self.path_of_video_being_downloaded = None
        self.pool = None
        print("Quit function: download")

    def start_download_subprocess(self, url, is_prefetching=False):
        """
        Starts the download subprocess. Specifies a special file name format and a preference in
        the quality of the videos. If the prefetching flag is set, then the download rate will be
        2 x slower.
        @param url: the url of the song .
        @param is_prefetching: the prefetching flag.
        @return: None
        """
        preferred_formats = ['18', '34', '43', '5', '44', '35', '17', '45', '22', '46', '37']
        preferred_formats = '/'.join(preferred_formats)

        args = ["youtube-dl"]
        args.extend(['-o', self.directory + '%(title)s.%(ext)s'])
        args.extend(['-f', preferred_formats])
        #args.append('-q')
        if is_prefetching:
            download_rate = self.max_download_rate // 2
        else:
            download_rate = self.max_download_rate

        args.extend(['-r', "%dk" % download_rate])
        args.append(url)

        self.download_subprocess = subprocess.Popen(args)

    def get_song_path_from_title(self, title):
        """
        Searches the song directory for the complete file path. Tries to find it via
        the name of the song and knowledge about the common file extensions.
        @param title: the title of the song
        @return: the full filepath of the song
        """
        # '.part' for when videos are still being downloaded
        extensions = ['.mp4', '.flv', '.webm',
                      '.mp4.part', '.flv.part', '.webm.part']
        # youtube-dl adds .part when file is still downloading

        # Fixes bug where ' would be used by youtube-dl and " by OS
        title_escaped = string.replace(title, '"', "'")

        #for extension in extensions:
        #    print("Possible extension: ", self.directory + title + extension)

        while True:
            for extension in extensions:
                path = unicode(self.directory + title + extension)
                if os.path.exists(path):
                    return path

                path = unicode(self.directory + title_escaped + extension)
                if os.path.exists(path):
                    return path

            time.sleep(0.2)
            print("No path: ", self.directory + title)

    def get_downloading_video_path(self):
        """
        Returns the filepath of the current file being downloaded if there is one.
        Otherwise, returns the filepath of the last file downloaded.
        @return: the path of the file.
        """
        if not self.is_downloading_now:
            return self.last_video_finished_filepath
        else:
            return self.path_of_video_being_downloaded

    def is_downloading(self):
        """
        @return: true if downloader is downloading, else false.
        """
        return self.is_downloading_now

    def is_song_already_downloaded(self, index):
        """
        Returns true if the song has already being downloaded, else false.
        @param index: the index of the song
        @return: true if the song has already being downloaded.
        """
        return index in self.downloaded_songs_indices

    def get_file_path(self, index):
        """
        Given an index, tries to find the filepath associated with it.
        @param index: the index of the song
        @return: the path of the file associated with the index
        """
        if index == self.current_song_index:
            return self.get_downloading_video_path()

        try:
            return self.downloaded_songs_paths[index]
        except IndexError:
            return ""

    def get_length(self, index):
        """
        Return the length of the file associated with that index.
        @param index: the index of the song
        @return: the length of the file.
        """
        return self.songs_metadata[index]['length']
