# coding=utf-8
class Video:
    def __init__(self, metadata_entry, index):
        self.author = self.get_author(metadata_entry)
        self.name = self.get_name(metadata_entry)
        self.url = self.get_url(metadata_entry)
        self.date = self.get_date(metadata_entry)
        self.length = self.get_length(metadata_entry)
        self.index = index

    def get_author(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'author', 0, 'name', '$t')

    def get_name(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'media$group', 'media$title', '$t')

    def get_url(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'link', 0, 'href')

    def get_date(self, metadata_entry):
        return self.try_to_get_attribute(metadata_entry, 'updated', '$t')


    def get_length(self, metadata_entry):
        """
        @return: the length of the video. If not found, return None
        """
        length = self.try_to_get_attribute(metadata_entry, 'media$group', 'yt$duration', 'seconds')
        if length:
            return int(length)

        length = self.try_to_get_attribute(metadata_entry, 'media$group', 'media$content', 0, 'duration')
        if length:
            return int(length)

        return None

    def try_to_get_attribute(self, entry, *args):
        """
        Given various attributes, tries extract them from the entry.
        Example: try_to_get_attribute(entry, 'data', 'result', 'length') tries
        to return entry['data']['result']['length']. Simple method to handle the
        necessary exception handling behind the scenes. If there is an error,
        None is returned.
        """
        try:
            result = entry
            for arg in args:
                result = result[arg]
            return result
        except AttributeError:
            return None

    def download(self):
        pass

    def prefetch(self):
        pass

    def stop_downloading(self):
        pass

    def get_index(self):
        pass