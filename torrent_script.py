import argparse
import shutil
from pathlib import Path
from collections import defaultdict
import logging

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

class DownloadCategorizer():
    """
    Categorizes file paths to list depending on the nature of their content.
    """

    title_dict = defaultdict(str)

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
        pass



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
args = parser.parse_args()

source = args.source[0]
destination = args.destination[0]
logging.basicConfig(filename='torrent_transfer.log', level=logging.WARNING)

def get_file_paths(source):
    """
    Gets all the video file path objects for the source directory.
    :param source: The source directory path
    :return: a list of all the downloaded video file Path objects
    """
    file_endings = ["mp4", "mp3", "avi", "mpg", "wmv", "mov", "mkv"]
    files = [file for file in source.glob("**/*")
             if file.is_file() and any([file.name.endswith(ending) for ending in file_endings])]
    return files

def episode_transfer(destination, episode):
    """
    transfers the file to destination with the following structure:

    * destination/Episodes/title/season/file

    :param destination: The destination directory of the the file
    :param episode: an Episode object
    :return: None
    """
    pass

def movie_transfer(destination, movie):
    """
    transfers the file to destination with the following structure:

    * destination/Movies/name/file

    :param destination: The destination directory of the the file
    :param movie: a Movie object
    :return: None
    """
    pass

def other_transfer(destination, other):
    """
    transfers the file to destination with the following structure:

    * destination/Other/file

    :param destination: The destination directory of the the file
    :param other: a path
    :return: None
    """
    pass

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
    categorizer.categorize(video_files)
    print("Number of files: " + str(len(video_files)))
    print("Episodes: " + str(len(categorizer.episodes)))
    print("Movies: " + str(len(categorizer.movies)))
    print("Other: " + str(len(categorizer.other)))
    print("Episodes Error: " + str(len(categorizer.episode_error)))
    print("Movie Error: " + str(len(categorizer.movie_error)))

    # Transfer the files
    for episode in categorizer.episodes:
        episode_transfer(destination, episode)
    for movie in categorizer.movies:
        movie_transfer(destination, movie)
    for other in categorizer.other:
        other_transfer(destination, other)
    logging.info("The file transfer process has successfully ended.")



process(source, destination)
