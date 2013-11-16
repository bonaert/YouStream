# coding=utf-8
import json
import os
import urllib2

DEFAULT_DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/songs/'
YOUTUBE_URL = 'https://gdata.youtube.com/feeds/api/videos?q=%s&alt=json&start_index=%d&max-results=%d'


def download_json(search_terms_list, start_index, max_results=10):
    """
    Downloads the Json from Youtube with the specific search terms,
    start index of the videos. Optionally, you can specify the maximum numbers of
    results (default: 10).
    @param search_terms_list: the search tokens
    @param start_index: the start index of the videos
    @param max_results: the maximum number of results
    @return: the Json downloaded from Youtube
    """
    url = YOUTUBE_URL % ('+'.join(search_terms_list), start_index, max_results)
    response = urllib2.urlopen(url).read()
    return json.loads(response)


def get_length_from_metadata_entry(entry):
    """
    Given an metadata entry, tries to extract the length of the video. If none
    is found in the metadata, returns None.
    @param entry: the entry
    @return: the length of the video. If not found, return None
    """
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

    return None


def get_entries(json_file):
    """
    Returns the entries found in the Json file.
    @param json_file: the json file
    @return: the entries found in the Json file.
    """
    try:
        return json_file['feed']['entry']
    except AttributeError:
        return []


def try_to_get_attribute(entry, *args):
    """
    Given various attributes, tries extract them from the entry.
    Example: try_to_get_attribute(entry, 'data', 'result', 'length') tries
    to return entry['data']['result']['length']. Simple method to handle the
    necessary exception handling behind the scenes.
    @param entry: the entry from the metadata
    @param args: the various attributes
    @return: the result if found. Otherwise, returns None.
    """
    try:
        result = entry
        for arg in args:
            result = result[arg]
        return result
    except AttributeError:
        return None


def get_metadata_from_entry(entry):
    # todo: (image? one day maybe)
    """
    Returns all the metadata found in the entry as a dictionary. It searches for name, length,
    url, author/poster, date posted and number of views.
    @param entry:
    @return:
    """
    return { 'author': try_to_get_attribute(entry, 'author', 0, 'name', '$t'),
             'name': try_to_get_attribute(entry, 'media$group', 'media$title', '$t'),
             'url': try_to_get_attribute(entry, 'link', 0, 'href'),
             'date': try_to_get_attribute(entry, 'updated', '$t'),
             'length': get_length_from_metadata_entry(entry) }


def get_metadata(json_file):
    """
    Returns all the video metadata found in the json file.
    @param json_file: the json file
    @return: all the video metadata found in the json file.
    """
    return [get_metadata_from_entry(entry) for entry in get_entries(json_file)]


def get_songs_metadata(search_terms, start_index=1, max_results=10):
    """
    From the search tokens, downloads the json file from Youtube and processes it.
    It extracts all metadata of the songs and returns it as a list. You can specify the
    start index, the maximum number of results wanted (Youtube may return less) and the maximum
    length of the videos (in minutes)
    @param search_terms: the search tokens (as a list)
    @param start_index: the start index of the videos (default: 1 (the beginning, because Youtube uses 1))
    @param max_results: the maximum number of results (there may be less)
    @return: the metadata extracted from the corresponding Youtube Json file
    """
    json_file = download_json(search_terms, start_index, max_results)
    return get_metadata(json_file)


def make_directory(directory):
    if not directory:
        directory = os.getcwd() + '/songs/'

    if not os.path.exists(directory):
        os.mkdir(directory)

    return directory