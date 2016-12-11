import argparse
import shutil
from pathlib import Path
from guessit import guessit
from collections import defaultdict
import logging
import re
import requests

class Movie:
    """
    The Movie class wraps movie file paths.
    """
    def __init__(self, title, path):
        self.title = title
        self.path = path

class Episode:
    """
    The Episode class wraps episode file paths.
    """
    def __init__(self, title, season, episode, path):
        self.title = title
        self.season = season
        self.episode = episode
        self.path = path

class CatigorizationFatalError(Exception):
    """
    Error class dedicated to Fatal Categorization errors.
    """
    def __init__(self, msg, cause):
        super(CatigorizationFatalError, self).__init__(msg)
        self.cause = cause

def episode_title_dictionary_value():
    """
    List that contains the title associated with the key
    and a number representing how many episodes are using that title.

    :return: A list value used in the episode title dictionary
    """
    return ["", 0]

class DownloadCategorizer():
    """
    Categorizes file paths to list depending on the nature of their content.
    """

    episode_title_dict = defaultdict(episode_title_dictionary_value)
    use_imdb = False

    def __init__(self):
        self.episodes = []
        self.movies = []
        self.episode_error = []
        self.movie_error = []
        self.other = []


    def categorize(self, list_of_paths):
        """
        Categorizes the paths in list_of_paths to:

        * Episodes if the path is determined to be a path to an episode
        * Movies if the path is determined to be a path to a movie
        * Other if the path cannot be determined to any category

        The paths will that are can be categorized to either an episode or a movie
        will be wrapped into an Episode or Movie object respectively.

        :param list_of_paths: The paths being categorized
        :return: None
        """
        print("Categorizing files....")
        for path in list_of_paths:
            self.categorize_(path)
        if self.use_imdb:
            print("Querying Imdb for title correction....")
            self.imdb_check_questionable_titles()
        print("Post processing titles....")
        self.post_process_titles()
        print("Filtering episodes from movies....")
        self.filter_episodes_from_movies()
        print("Correcting faulty episode numbers....")
        self.process_lost_episodes()
        print("Correcting faulty seasons....")
        self.process_lost_seasons()

    def categorize_(self, path):
        """
        Categorizes a single path to a list.

        :param path: A path being categorized.
        :return: None
        """
        try:
            guessit_result = guessit(str(path))
            if guessit_result["type"] == "episode":
                self.parse_episode(guessit_result, path)
            if guessit_result["type"] == "movie":
                self.parse_movie(guessit_result, path)
        except Exception as error:
            self.other.append(path)
            logging.error("guessit failed to guess path: {0}: {1}".format(path, str(error)))

    def parse_episode(self, guessit_episode, path):
        """
        Parses an episode into an Episode object and adds it to an appropriate list.

        :param guessit_episode: The result from guessit expected type is 'episode'
        :param path: The path of the video file
        :return: None
        """
        title = str(guessit_episode["title"]).title() if "title" in guessit_episode else None
        season = "Season " + str(guessit_episode["season"]) if "season" in guessit_episode else None
        episode = "Episode " + str(guessit_episode["episode"]) if "episode" in guessit_episode else None
        episode_object = Episode(title, season, episode, path)

        if title and season and episode:
            self.episodes.append(episode_object)
        else:
            self.episode_error.append(episode_object)

    def parse_movie(self, guessit_movie, path):
        """
        Parses a move into an Movie object and adds it to an appropriate list.

        :param guessit_episode: The result from guessit expected type is 'movie'
        :param path: The path of the video file
        :return: None
        """
        title = str(guessit_movie["title"]).title() if "title" in guessit_movie else None
        movie_object = Movie(title, path)
        if title:
            self.movies.append(movie_object)
        else:
            self.movie_error.append(movie_object)
            logging.error("Parsing failed for guessit_movie: {0}: 'title'".format(path))

    def post_process_titles(self):
        """
        Post processes titles for episodes in the list episodes.
        Does a best effort to correct wrong titles and merge similar titles to one.

        :return: None
        """
        all_episodes = self.episodes + self.episode_error
        for episode in all_episodes:
            key = self.title_key(episode.title)
            dict_tuple = self.episode_title_dict[key]
            dict_tuple[1] += 1 # Increment counter
            current_title = dict_tuple[0]
            self.episode_title_dict[key][0] = episode.title if len(episode.title) > len(current_title) else current_title

        for episode in all_episodes:
            key = self.title_key(episode.title)
            dict_tuple = self.episode_title_dict[key]
            if dict_tuple[1] < 3:
                more_common_tuple = self.find_more_common_title(episode)
                if more_common_tuple:
                    dict_tuple[1] -= 1
                    more_common_tuple[1] += 1
                    episode.title = more_common_tuple[0]

        for episode in all_episodes:
            episode.title = self.episode_title_dict[self.title_key(episode.title)][0]

    def title_key(self, title):
        """
        Returns a key into the title dictionary for the title.

        :param title: The title being handed a key
        :return: The title
        """
        return re.sub("\W","", title).lower()

    def find_more_common_title(self, episode):
        """
        Tries to find a more common title for the given episode object.
        Either in the path or in the post or prefix of the current title where the fix
        smalles unit is a word.

        :param episode: The episode object for the path
        :return: A more common title tuple if found else None
        """
        current_tuple = self.episode_title_dict[self.title_key(episode.title)]

        parts = list(episode.path.parts)
        title = re.sub("[.\-_]+", " ", episode.title)
        prefixes = [" ".join(title.split()[:i]) for i in range(1, len(title.split()) + 1)]
        postfixes = [" ".join(title.split()[i:]) for i in range(len(title.split()))]
        parts += prefixes if prefixes else []
        parts += postfixes if postfixes else []
        for part in sorted(list(set(parts)), key=lambda x: len(x)):
            key = self.title_key(part)
            if key in self.episode_title_dict:
                dict_tuple = self.episode_title_dict[key]
                if dict_tuple[1] > current_tuple[1]:
                    return dict_tuple
        return None


    def process_lost_seasons(self):
        """
        Does best effort to find lost seasons in paths not found by guessit.

        :return: None
        """
        lost_season = [e for e in self.episode_error if not e.season]
        self.episode_error = [e for e in self.episode_error if e.season]
        for episode in lost_season:
            match = [p for p in episode.path.parts if re.findall("season|sería|s[0-9]+|^[0-9]+$|", p.lower())]
            numbers = [n[0] for n in [re.findall("[0-9]+", m) for m in match] if n]
            episode.season = "Season " + str(int(numbers[0])) if numbers else None
            self.episodes.append(episode) if episode.title and episode.season and episode.episode else self.episode_error.append(episode)

    def process_lost_episodes(self):
        """
        Does best effort to find the lost episode number in paths not found by guessit

        :return: None
        """
        lost_episodes = [e for e in self.episode_error if not e.episode]
        self.episode_error = [e for e in self.episode_error if e.episode]
        for episode in lost_episodes:
            numbers = re.findall("[0-9]+", episode.path.name)
            episode.episode = "Episode " + str(int(numbers[0])) if numbers else None
            self.episodes.append(episode) if episode.episode and episode.title and episode.season else self.episode_error.append(episode)

    def log_errors(self):
        """
        Logs perceivable errors from the categorization.

        :return: None
        """
        for episode in self.episode_error:
            not_found = [key[1] for key in [(episode.title, "title"), (episode.season, "season"), (episode.episode, "episode")] if not key[0]]
            if not_found:
                logging.error("Parsing failed for guessit_episode: {0}: {1}".format(str(episode.path).encode(encoding="utf-8"), not_found))

    def filter_episodes_from_movies(self):
        """
        Filters episode titles found in movies and adds them to episodes list.

        :return: None
        """
        movies = self.movies.copy()
        self.movies = []
        for movie in movies:
            key = self.title_key(movie.title)
            if key in self.episode_title_dict:
                episode = Episode(self.episode_title_dict[key],None, None, movie.path)
                self.episode_error.append(episode)
            else: self.movies.append(movie)

    def imdb_check_questionable_titles(self):
        """
        Groups together questionable titles and queries imdb for correction.

        :return: None
        """
        all_episodes = self.episodes + self.episode_error
        count_dict = defaultdict(episode_title_dictionary_value)
        for episode in all_episodes:
            count_dict[self.title_key(episode.title)][1] += 1

        questionable = [e for e in all_episodes if len(e.title.split()) == 1 or re.search("[0-9]+", e.title)
                        or count_dict[self.title_key(e.title)][1] < 3]
        title_dict = defaultdict(str)           # Query this before making requsest, contains answers from previous requests
        correct_titles = defaultdict(str)       # Contains correction for a title

        for episode in questionable:
            key = self.title_key(episode.title)
            if key in correct_titles:
                episode.title = correct_titles[key]
                continue
            str_path = self.title_key(str(episode.path))
            queries = self.get_episode_queries(episode)
            for query in queries:
                title = None
                query_key = self.title_key(query)
                if query_key in title_dict:
                    title = title_dict[query_key]
                else:
                    try:
                        title = self.query_imdb_for_title_(query)
                    except requests.ConnectionError as error:
                        logging.critical("Connection error occurred during imdb communication: {0}".format(str(error)))
                        raise CatigorizationFatalError("Internet error occured: Internet communication failed.", error)
                if title and self.title_key(title) in str_path:
                    correct_titles[key] = title
                    title_dict[query_key] = title
                    old_title = episode.title
                    episode.title = title.title()
                    if len(title) >= len(old_title):
                        break
                elif title:
                    title_dict[query_key] = title

    def get_episode_queries(self, episode):
        """
        Gets appropriate imdb queries for the episode.

        :param episode: The episode being queried to imdb.
        :return: list of queries
        """
        key = self.title_key(episode.title)
        path = Path(re.sub("[.\-_]+", " ", str(episode.path)))
        queries = [" ".join(part.split()[:i]) for part in path.parts for i in range(1, len(part.split()) + 1)]
        queries += [" ".join(part.split()[i:]) for part in path.parts for i in range(len(part.split()))]
        queries = [q for q in queries if self.title_key(q) in key or key in self.title_key(q)]
        return [episode.title] + list(set(queries))

    def query_imdb_for_title_(self, query):
        """
        Queries imdb for title.

        :param query: The query being sent
        :return: the title found for query else None
        """
        response = requests.get("https://www.omdbapi.com/", {"t": query})
        json_result = response.json()
        if "Title" in json_result:
            return json_result["Title"]
        return None

def source_path(path):
    """
    Checks if the source path is a valid directory path.

    :param path: a path being validated
    :return: The path as a Path object
    :raises ArgumentTypeError: if path is not a valid directory path or if directory
            doesn't exist.
    """
    try:
        p = Path(path)
        if not p.exists():
            raise Exception("Directory doesn't exist.")
        if not p.is_dir():
            raise Exception("Path doesn't lead to a directory.")
        return p
    except Exception as error:
        raise argparse.ArgumentTypeError("{0} is not a valid directory path: {1}".format(path, str(error)))

def destination_path(path):
    """
    Checks if destination path is valid and creates the destination
    directory if it doesn't exist.

    :param path: The input destination path
    :return: the destination directory path as a Path object
    :raises ArgumentTypeError: if path is not a valid directory path
    """
    try:
        p = Path(path)
        if not p.is_dir():
            p.mkdir()
        return p
    except:
        raise argparse.ArgumentTypeError("{0} is not a valid directory path.".format(path))


parser = argparse.ArgumentParser(description="Moves and sorts torrented files from a download directory to a source directory")
parser.add_argument("source", metavar="S", type=source_path, nargs=1, help="The source directory path")
parser.add_argument("destination", metavar="D", type=destination_path, nargs=1, help="The destination directory path")
parser.add_argument("-i" , "--imdb", action="store_true", help="Use internet queries to IMDB (Internet movie database) to resolve questionable titles")
args = parser.parse_args()

source = args.source[0]
destination = args.destination[0]
DownloadCategorizer.use_imdb = args.imdb
logging.basicConfig(filename='torrent_transfer.log', level=logging.WARNING, filemode="w")

def get_file_paths(source):
    """
    Gets all the video file path objects for the source directory.

    :param source: The source directory path
    :return: a list of all the downloaded video file Path objects
    """
    print("Gathering files please wait....")
    file_endings = ["mp4", "avi", "mpg", "wmv", "mov", "mkv"]
    files = [file for file in source.glob("**/*")
             if file.is_file() and any([file.name.endswith(ending) for ending in file_endings])]
    return files

def video_transfer(destination, prefix, video):
    """
    transfers the file to destination with the following structure:

    * destination/prefix/title/season/file    if the video is an episode
    * destination/prefix/title/file             if the video in a movie

    :param destination: The destination directory of the the file
    :param prefix: The name of the parent folder for this file
    :param video: an Episode or a Movie object
    :return: None
    """
    try:
        object_dir = dir(video)
        destination = destination / prefix if prefix else destination
        destination = destination / video.title
        destination = destination / video.season if "season" in object_dir and video.season else destination
        destination = destination / video.episode if "episode" in object_dir and video.episode else destination
        if not destination.exists():
            destination.mkdir(parents=True)
        shutil.move(str(video.path), str(destination))
    except Exception as error:
        logging.fatal("Video transfer failed for source: {0} and destination {1}: {2}"
                      .format(str(video.path).encode("utf8"), str(destination), str(error)))

def process(source, destination):
    """
    Starts the file transfer process.

    :param source: The source directory from where the files can be found.
    :param destination: The destination directory to which the files will be transferred.
    :return: None
    """
    logging.info("Starting the file transfer process.")
    video_files = get_file_paths(source)
    categorizer = DownloadCategorizer()
    try:
        categorizer.categorize(video_files)
    except CatigorizationFatalError as error:
        msg = "A fatal categorization error occurred aborting transfer: {0}".format(str(error))
        logging.fatal(msg)
        print(msg)
        exit(-1)

    print("Number of files:" + str(len(video_files)))
    print("Episodes: " + str(len(categorizer.episodes + categorizer.episode_error)))
    print("Movies: " + str(len(categorizer.movies + categorizer.movie_error)))
    categorizer.log_errors()
    # Transfer the files
    for episode in categorizer.episodes + categorizer.episode_error:
        video_transfer(destination, "Episodes", episode)
    for movie in categorizer.movies:
        video_transfer(destination, "Movies", movie)
    logging.info("The file transfer process has successfully ended.")



process(source, destination)
