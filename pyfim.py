import os
import sys
import syslog
import xml.etree.ElementTree as tree
import hashlib
import time

# Insert alternative Path here
xmlconfig = "./config.xml"
#

syslog.syslog(syslog.LOG_WARNING, "pyfim-[START]")
start_time = time.time()
if not os.path.exists(xmlconfig) or os.path.getsize(xmlconfig) < 1:
    syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR,END] config.xml doesn't exist or is empty")
    sys.exit(-1)
dbpath = "./pyfim.db"
dbupdate = list()
path_ignore = ""
path_norm = ""
path_meta = ""
xmldata = tree.parse(xmlconfig)
xmlroot = xmldata.getroot()

for x in xmlroot:
    try:
        ignore = x.findtext('ignore')
        checkmeta = x.findtext('checkmeta')
        path = x.findtext('path')
        if ignore == "yes" and path:
            path_ignore = path_ignore + f"{path},"
        elif checkmeta == "yes" and path:
            path_meta = path_meta + f"{path},"
        elif checkmeta == "no" and path:
            path_norm = path_norm + f"{path},"
    except:
        syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR] Failure when reading config.xml")

if not path_meta and not path_norm:
    syslog.syslog(syslog.LOG_WARNING,
                  f"pyfim-[ERROR,END] Skipping Scan or Database because no Paths/Files are configured.")
    sys.exit(1)
else:
    syslog.syslog(syslog.LOG_WARNING, f"pyfim-[CONFIG] Scanning:{path_norm}")
    syslog.syslog(syslog.LOG_WARNING, f"pyfim-[CONFIG] Scanning with Meta:{path_meta}")
    syslog.syslog(syslog.LOG_WARNING, f"pyfim-[CONFIG] Ignoring:{path_ignore}")


    def writeDB(dbupdate):
        with open('./pyfim.db', 'w') as f:
            for line in dbupdate:
                f.write(f"{line}\n")


    def compareAndUpdateDB(dbupdate):
        dbcompare = list()
        with open("./pyfim.db", "r") as f:
            for line in f:
                dbcompare.append(line.replace("\n", ""))
        for entryUp in dbupdate:
            parts = entryUp.split(";")
            if any(str(parts[0]) in s for s in dbcompare):
                if entryUp in dbcompare:  # same
                    continue
                else:  # modified
                    file = parts[0].replace('path:', '')
                    oldFileHash = \
                        dbcompare[dbcompare.index(next((s for s in dbcompare if parts[0] in s), None))].split(";")[
                            1].replace(
                            "sha256:", "")
                    newFileHash = parts[1].replace("sha256:", "")
                    oldStatHash = \
                        dbcompare[dbcompare.index(next((s for s in dbcompare if parts[0] in s), None))].split(";")[
                            2].replace(
                            "stat:", "")
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
                newFileHash = parts[1].replace("sha256:", "")
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
            if not any(str(parts[0]) in s for s in dbupdate):  # deleted
                file = parts[0].replace('path:', '')
                FileHash = parts[1].replace("sha256:", "")
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


    def getListOfFiles(dirNames):
        dirNames = dirNames.split(",")
        allFiles = list()
        listOfFile = list()
        for dir in dirNames:
            if dir:
                if not os.path.exists(dir):
                    syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR] Dir not found:{dir}, Dir deleted or Check Config")
                    continue
                if os.path.isdir(dir):
                    allFiles.append(dir)
                if not os.path.isfile(dir):
                    listOfFile = os.listdir(dir)
                else:
                    listOfFile.append(dir)
                # Iterate over all the entries
                for entry in listOfFile:
                    # Create full path
                    fullPath = os.path.join(dir, entry)
                    if fullPath not in path_ignore:
                        # If entry is a directory then get the list of files in this directory
                        if os.path.isdir(fullPath):
                            allFiles = allFiles + getListOfFiles(fullPath)
                        else:
                            allFiles.append(fullPath)
                    else:
                        continue
        return allFiles


    path_meta_files = getListOfFiles(path_meta)
    path_norm_files = getListOfFiles(path_norm)

    for file in path_meta_files:
        try:
            if os.path.isfile(file):
                meta_hash = hashlib.sha256(str(os.stat(file)).encode('utf-8'))
                hash = hashlib.sha256()
                with open(file, 'rb') as f:
                    while True:
                        data = f.read(64000)
                        if not data:
                            break
                        hash.update(data)
                        sha256 = hash.hexdigest()
                dbupdate.append(f"path:{file};sha256:{sha256};stat:{meta_hash.hexdigest()}")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha256(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha256:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            pass

    for file in path_norm_files:
        try:
            if os.path.isfile(file):
                hash = hashlib.sha256()
                with open(file, 'rb') as f:
                    while True:
                        data = f.read(64000)
                        if not data:
                            break
                        hash.update(data)
                        sha256 = hash.hexdigest()
                dbupdate.append(f"path:{file};sha256:{sha256};stat:")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha256(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha256:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            pass

    if os.path.exists("./pyfim.db") and os.path.getsize("./pyfim.db") > 0:
        compareAndUpdateDB(dbupdate)
        syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Update Database")
        writeDB(dbupdate)
    else:
        syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Create Database")
        writeDB(dbupdate)

    syslog.syslog(syslog.LOG_WARNING, f"pyfim-[END] Scan took:{round((time.time() - start_time), 5)} Sec")
    sys.exit(1)
