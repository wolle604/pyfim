#cython: language_level=3
import hashlib
import os
import syslog


def getGenExp(str path, files):
    return (s for s in files  if path  in s)

def getListComp(str path, files):
    return [s for s in files  if path  in s]

def compareAndUpdateDB(dbupdate):
    dbcompare = list()
    with open("./pyfim.db", "r") as f:
        for line in f:
            dbcompare.append(line.strip("\n"))
    for entryUp in dbupdate:
        parts = entryUp.split(";")
        pathforlistcomp = r"%s;" % (parts[0])
        entry = getGenExp(pathforlistcomp, dbcompare).__next__()
            #(s for s in dbcompare if pathforlistcomp in s).__next__()
        if entry:
            if entryUp in dbcompare:  # same
                continue
            else:  # modified
                file = parts[0].replace('path:', '')
                oldFileHash = dbcompare[dbcompare.index(entry)].split(";")[1].replace("sha1:", "")
                newFileHash = parts[1].replace("sha1:", "")
                oldStatHash = \
                    dbcompare[dbcompare.index(entry)].split(";")[
                        2].replace("stat:", "")
                newStatHash = parts[2].replace("stat:", "")
                if oldStatHash == newStatHash and not oldStatHash and oldFileHash != newFileHash:
                    tag = "[FILE]"
                elif oldFileHash == newFileHash and not oldFileHash and oldStatHash != newStatHash:
                    tag = "[DIR]"
                else:
                    tag = "[FILE,META]"
                syslog.syslog(syslog.LOG_CRIT,
                              f"pyfim-{tag} Modified:{file}, Old-File-Hash:{oldFileHash}, New-File-Hash:{newFileHash}, Old-Meta-Hash:{oldStatHash}, New-Meta-Hash:{newStatHash}")
                continue
        else:  # added
            file = parts[0].replace('path:', '')
            newFileHash = parts[1].replace("sha1:", "")
            newStatHash = parts[2].replace("stat:", "")
            if newFileHash and not newStatHash:
                tag = "[FILE]"
            elif not newFileHash and newStatHash and os.path.isdir("file"):
                tag = "[DIR]"
            else:
                tag = "[FILE,META]"
            syslog.syslog(syslog.LOG_CRIT,
                          f"pyfim-{tag} Added:{file}, File-Hash:{newFileHash}, Meta-Hash:{newStatHash}")
            continue
    for entryComp in dbcompare:
        parts = entryComp.split(";")
        pathforlistcomp = "%s;" % (parts[0])
        entry = getGenExp(pathforlistcomp, dbupdate)
            #(s for s in dbupdate if pathforlistcomp in s)
        if not hasGeneratorExprElements(entry):  # deleted
            file = parts[0].replace('path:', '')
            FileHash = parts[1].replace("sha1:", "")
            StatHash = parts[2].replace("stat:", "")
            if FileHash and not StatHash:
                tag = "[FILE]"
            elif not FileHash and StatHash and os.path.isdir("file"):
                tag = "[DIR]"
            else:
                tag = "[FILE,META]"
            syslog.syslog(syslog.LOG_CRIT,
                          f"pyfim-{tag} Deleted:{file}, File-Hash:{FileHash}, Meta-Hash:{StatHash}")
            continue

def hasGeneratorExprElements(iterable):
    try:
        return next(iterable)
    except StopIteration:
        return False

def calcHashNorm(path_norm_files, dbupdate):
    for file in path_norm_files:
        try:
            if os.path.isfile(file):
                hash = hashlib.sha1()
                with open(file, 'rb') as f:
                    while True:
                        data = f.read(65536)
                        if not data:
                            break
                        hash.update(data)
                        sha1 = hash.hexdigest()
                dbupdate.append(f"path:{file};sha1:{sha1};stat:")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha1:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            pass
    return dbupdate

def calcHashMeta(list path_meta_files, dbupdate):
    for file in path_meta_files:
        try:
            if os.path.isfile(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                hash = hashlib.sha1()
                with open(file, 'rb') as f:
                    while True:
                        data = f.read(65536)
                        if not data:
                            break
                        hash.update(data)
                        sha1 = hash.hexdigest()
                dbupdate.append(f"path:{file};sha1:{sha1};stat:{meta_hash.hexdigest()}")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha1:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            pass
    return dbupdate

def concatLists(list lst1 , list lst2):
    return lst1.extend(lst2)

#[]