# YStream is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# YStream is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with YStream. If not, see <http://www.gnu.org/licenses/>.
#


import time
import json
import os
import optparse
from Queue import Queue
from multiprocessing.pool import ThreadPool
import sys

import requests
import mplayer
from pytube import YouTube


default_directory = os.path.dirname(os.path.realpath(__file__)) + '/songs/'


def get_content(url):
    return requests.get(url)


def download_json(search_terms):
    url = 'https://gdata.youtube.com/feeds/api/videos?q=%s&alt=json' % ('+'.join(search_terms))
    response = get_content(url)
    return json.loads(response.content)


def get_length(entry):
    try:
        length = entry['media$group']['yt$duration']['seconds']
        return int(length)
    except KeyError:
        pass

    try:
        length = entry['media$group']['media$content'][0]['duration']
        return int(length)
    except KeyError:
        pass

    return -1


def get_all_urls(json_file, max_length, num_songs, number_of_skipped_songs):
    feed = json_file['feed']
    urls = []

    entries = feed.get('entry', [])[number_of_skipped_songs:]
    for entry in entries:
        length = get_length(entry)

        if 0 < length <= max_length * 60:
            try:
                url = entry['link'][0]['href']
                urls.append(url)
            except AttributeError:
                pass

        if len(urls) == num_songs:
            return urls

    return urls


def get_extension(video):
    extension = ['mp4', 'flv', 'mp3', '.3gp']

    for extension in extension:
        if video.filter(extension):
            return extension


def get_video_and_extension(url):
    youtube = YouTube()
    youtube.url = url
    extension = get_extension(youtube)
    return min(youtube.filter(extension=extension)), extension


class Player():
    def __init__(self, search_terms, directory=default_directory, delete_videos_after_watching=False,
                 keep_complete_videos=False, max_length=8, num_videos_to_prefetch=4,
                 fullscreen=False, number_of_skipped_songs=0, num_songs=-1):

        self.directory = directory
        self.keep_complete_videos = keep_complete_videos
        self.delete_videos_after_watching = delete_videos_after_watching
        self.num_videos_to_prefetch = num_videos_to_prefetch
        self.fullscreen = fullscreen

        self.pool = None
        self.jobs = self.get_jobs(search_terms, max_length, number_of_skipped_songs, num_songs)
        if self.jobs.qsize() == 0:
            print "No videos were found!"
            sys.exit()

        self.player = None
        self.interval = 0.2

        self.is_downloading_now = False
        self.video_being_downloaded = None
        self.is_opened_video_being_downloaded = False

        self.paths_of_ready_files = []
        self.paths_of_downloaded_songs = set()

        self.opened_song_path = None

    def get_jobs(self, search_terms, max_length, number_of_skipped_songs, num_songs):
        jobs = Queue()

        json_file = download_json(search_terms)

        urls = get_all_urls(json_file, max_length, num_songs, number_of_skipped_songs)
        for url in urls:
            jobs.put(url)

        return jobs

    def get_video_and_filepath(self, url):
        video, extension = get_video_and_extension(url)
        filepath = self.directory + video.filename + '.' + extension
        return video, filepath

    def save_video(self, video, filepath):
        print "\n%s\n" % video.filename

        video.download_wait_until_end_and_quit(self.directory)

        # If song was not already downloaded
        if filepath not in self.paths_of_downloaded_songs:
            self.paths_of_ready_files.append(filepath)

        # If song playing that was downloading has stopped, don't add to the ready songs,
        # since we are already playing now 
        if self.is_opened_video_being_downloaded and self.opened_song_path == filepath:
            self.paths_of_ready_files.pop()

        self.paths_of_downloaded_songs.add(filepath)
        self.is_downloading_now = False
        self.video_being_downloaded = None

    def is_player_running(self):
        return self.player and self.player.is_alive() and self.player.length is not None

    def stop_download(self):
        if self.pool:
            self.pool.terminate()
            self.is_downloading_now = False
            self.pool = None
            self.video_being_downloaded = None

    def skip_download_of_song(self, filepath=None):
        if self.is_downloading_now:
            self.stop_download()

        if filepath:
            self.paths_of_downloaded_songs.add(filepath)

    def download_next_song(self, video, filepath):
        try:
            self.video_being_downloaded = filepath
            self.pool = ThreadPool(processes=1)
            self.pool.apply_async(self.save_video, args=(video, filepath))
            self.pool.close()

            # Allow some time for thread to start, make connection and start download
            # and get the first 1.5 MB
            megabit = (1024 * 1024)
            while not os.path.exists(filepath) or os.path.getsize(filepath) < 1.5 * megabit:
                time.sleep(0.5)

            time.sleep(1)
        except (OSError, IOError):
            self.skip_download_of_song(filepath)

    def get_next_song(self):
        self.stop_download()

        url = self.jobs.get()
        try:
            video, filepath = self.get_video_and_filepath(url)
        # Strange bug in pytube implementation when downloading some video
        except IndexError:
            self.skip_download_of_song()
            return

        # If song does not already exist, download it
        need_to_download = (not os.path.exists(filepath))
        self.is_downloading_now = need_to_download

        if need_to_download:
            self.download_next_song(video, filepath)
        else:
            self.skip_download_of_song(filepath)
            self.paths_of_ready_files.append(filepath)

    def is_there_complete_downloaded_songs(self):
        return self.paths_of_ready_files != []

    def start_next_song(self):
        if self.player:
            self.player.quit()

        self.is_opened_video_being_downloaded = not self.is_there_complete_downloaded_songs()

        if self.is_there_complete_downloaded_songs():
            self.opened_song_path = self.paths_of_ready_files.pop(0)
        else:
            self.opened_song_path = self.video_being_downloaded

        self.player = mplayer.Player()

        self.player.loadfile(self.opened_song_path)
        if self.fullscreen:
            self.player.fullscreen = True

    def song_was_skipped(self, percent_song_played):
        skipped_song_percentage = 10
        return skipped_song_percentage >= percent_song_played > 0

    def was_in_middle_of_song(self, percent_song_played):
        skipped_song_percentage = 7
        return 98 > percent_song_played > skipped_song_percentage

    def start(self):
        percent_played = 0

        while True:
            try:
                player_is_stopped = not self.is_player_running()

                # Seek percentage of song remaining
                if self.is_player_running():
                    try:
                        percent_played = self.player.time_pos / float(self.player.length) * 100
                    except TypeError:
                        # If player stopped meanwhile
                        player_is_stopped = True
                else:
                    # We want to keep the percentage in which the video was before being closed
                    # Because that allows us to know if video was skipped or ended naturally
                    # Therefore we don't update the percentage if the player is stopped
                    pass

                # If there are no more songs
                if player_is_stopped and not self.is_downloading_now and self.jobs.empty():
                    print "\nNo more songs!"
                    self.quit()

                # If player is not running and song is in the middle, take that as quit. If song
                # is at beginning (upto 7% of song), take that as go to next song and don't do anything.
                if player_is_stopped and self.was_in_middle_of_song(percent_played):
                    self.quit()

                song_was_skipped = self.song_was_skipped(percent_played)
                song_was_being_downloaded = self.is_opened_video_being_downloaded

                # If song was skipped and being downloaded at the same time, stop downloading it.
                if player_is_stopped and song_was_skipped and song_was_being_downloaded:
                    self.stop_download()

                    self.paths_of_downloaded_songs.add(self.opened_song_path)
                    self.is_downloading_now = False
                    self.is_opened_video_being_downloaded = False
                    self.video_being_downloaded = None

                # If video was skipped, delete if its incomplete
                if player_is_stopped and self.opened_song_path is not None and song_was_skipped:
                    if song_was_being_downloaded or not self.keep_complete_videos:
                        os.remove(self.opened_song_path)
                        self.opened_song_path = None

                        # If the song ended and the user wants to delete it, delete the song
                if player_is_stopped and self.opened_song_path is not None and self.delete_videos_after_watching:
                    os.remove(self.opened_song_path)
                    self.opened_song_path = None

                # Get next song if previous download stopped
                must_download = len(
                    self.paths_of_ready_files) < self.num_videos_to_prefetch or self.paths_of_ready_files == []
                if not self.is_downloading_now and not self.jobs.empty() and must_download:
                    self.get_next_song()

                # If song has stopped, try to start next one (if download ended)
                there_is_song_to_play = (self.paths_of_ready_files != [] or self.is_downloading_now)
                if player_is_stopped and there_is_song_to_play:
                    self.start_next_song()

                time.sleep(self.interval)

            except KeyboardInterrupt:
                self.quit()

    def try_to_remove_file(self, path):
        try:
            os.remove(path)
        except (IOError, OSError):
            pass

    def quit(self):
        # Stop downloading
        if self.pool:
            self.pool.terminate()

        delete_opened_song = self.is_opened_video_being_downloaded or not self.keep_complete_videos

        # Delete current file if wanted
        if self.opened_song_path is not None and (self.delete_videos_after_watching or delete_opened_song):
            os.remove(self.opened_song_path)

        # Delete song being downloaded
        if self.is_downloading_now:
            self.try_to_remove_file(self.video_being_downloaded)

        # Delete all songs to be played next (user never saw them) and already downloaded
        for path in self.paths_of_ready_files:
            self.try_to_remove_file(path)

        sys.exit(0)


if __name__ == '__main__':

    print """
    YStream is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    YStream is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with YStream. If not, see <http://www.gnu.org/licenses/>.

    This version depends on pytube, which can not always get the desired video, which
    may lead to strange bugs with the skipped songs and number of songs to play flags.

    """

    usage = "usage: %prog [options] arg1 arg2 ... "
    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-d", "--delete", action='store_true', dest='delete_videos', default=False,
                      help="Delete files after exit")

    parser.add_option('-f', '--filepath', action="store", dest="directory", default=default_directory,
                      help="Choose the directory in which the videos will be stored")

    parser.add_option('-r', '--remove', action="store_true", dest="remove_complete_skipped_videos", default=False,
                      help="Remove skipped song even if download is complete")

    parser.add_option('-m', '--minutes', action="store", dest="max_length", type=int, default=6,
                      help="Choose videos with length at most ... minutes. (max 4 hours)")

    parser.add_option('-p', '--prefetch', action="store", dest="num_videos_to_prefetch", type=int, default=2,
                      help="Prefetch the next ... videos if current download ended (max 10)")

    parser.add_option('--fs', '--fullscreen', action="store_true", dest="fullscreen", default=False,
                      help="Set the video to fullscreen")

    parser.add_option('-s', '--skip', action="store", dest="number_of_skipped_songs", type=int, default=0,
                      help="Skip the first ... songs(max 15).")

    parser.add_option('-n', '--num_songs', action="store", dest="number_songs", type=int, default=-1,
                      help="Play only ... songs. Default:-1 (all)")

    (options, args) = parser.parse_args()

    # No search terms
    if len(args) == 0:
        parser.error("Need at least one search term")

    # Invalid maximum length
    if not 0 <= options.max_length <= 4 * 60:
        parser.error("Please, enter a reasonable amount of minutes. (1 min upto 4 hours)")

    # Invalid number of videos to prefetch
    if not 0 <= options.num_videos_to_prefetch <= 10:
        parser.error("Please enter a number of songs to prefetch between 0 and 10")

    # Invalid number of skipped song
    if not 0 <= options.number_of_skipped_songs <= 15:
        parser.error("Please enter a number of songs to skip between 0 and 15")

    # Invalid number of songs
    if not (options.number_songs > 0 or options.number_songs == -1):
        parser.error("Enter a positive number of songs to skip.")

    # If directory doesn't exist, try to create it
    if not os.path.isdir(options.directory):
        try:
            os.makedirs(options.directory)
        except (OSError, IOError):
            parser.error(
                "Can't create songs folder.\n Please allow it or choose an existing directory with the -f flag.")

    player = Player(search_terms=args, delete_videos_after_watching=options.delete_videos, directory=options.directory,
                    keep_complete_videos=(not options.remove_complete_skipped_videos), max_length=options.max_length,
                    num_videos_to_prefetch=options.num_videos_to_prefetch, fullscreen=options.fullscreen,
                    number_of_skipped_songs=options.number_of_skipped_songs, num_songs=options.number_songs)

    player.start()