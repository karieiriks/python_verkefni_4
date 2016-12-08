import shutil
import glob
import os
import re
import pip
from guessit import guessit

def make_dir(name_of_dir):
    os.makedirs(name_of_dir)

def move_to_dir(path, file):
    shutil.move(file, path)

def move():
    end = ['avi','mkv','mp4','mov','AVI']
    target = 'result\\'
    shows = 'Season\\'
    slash = '\\'
    files = [val for sublist in [[os.path.join(i[0], j) for j in i[2]] for i in
                                 os.walk('downloads\\')] for val in sublist]
    #print(len(files))
    #for i in range(1000, 1010) :
       # print (files[i][-3:], files[i])
    files = [x for x in files if x[-3:] in end]
   # print (len(files))
    #for i in range(1000, 1010) :
      #  print (files[i][-3:], files[i])

    names = [x.split('\\') for x in files]
    names = [x[-1] for x in names]
    print (len(files))
    print (len(names))
   # for i in range(1000, 1010) :
     #   print (names[i])
    path_names = list(map(list, zip(files, names)))
    #print (path_names[:10])

    counter = 1
    for i in path_names :
        print (len(path_names), counter)
        counter += 1
        a = guessit(i[1])
        print (a)
        try :
            title = a['title']
        except KeyError :
            title = 'Unknown'
        try :
            file_type = a['type']
        except KeyError :
            file_type = 'Other'
        print (file_type, title)
        if file_type == 'episode' :
            try :
                season = a['season']
                path = target + file_type + slash + title + slash + 'Season ' + str(a['season'])
                print (season)
            except KeyError :
                path = target + file_type + slash + title
        elif file_type == 'movie' :
            path = target + file_type + slash + title
        else :
            path = target + 'Other'
        print(path)
        filename = i[0]
        try :
            if not os.path.exists(path):
                make_dir(path)
        except os.Error :
            pass
        try :
            if not os.path.exists(path + slash + filename):
                move_to_dir(path, filename)
        except shutil.Error :
            pass

print (move())



