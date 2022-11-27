import os
import sys
import syslog
import hashlib
import xml.etree.ElementTree as tree
import time
def calcHashNorm(path_norm_files, dbupdate):
    for i in range(len(path_norm_files)):
        try:
            file = path_norm_files[i]
            if os.path.isfile(file):
                hash = hashlib.sha1()
                with open(file, 'rb') as f:
                    for chunk in iter(lambda: f.read(524288), b""):
                        hash.update(chunk)
                dbupdate.append(f"path:{file};sha1:{hash.hexdigest()};stat:")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha1:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR] {e}")
    return dbupdate


def calcHashMeta(path_meta_files, dbupdate):
    for i in range(len(path_meta_files)):
        try:
            file = path_meta_files[i]
            if os.path.isfile(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                hash = hashlib.sha1()
                with open(file, 'rb') as f:
                        for chunk in iter(lambda: f.read(524288), b""):
                            hash.update(chunk)
                dbupdate.append(f"path:{file};sha1:{hash.hexdigest()};stat:{meta_hash.hexdigest()}")
            elif os.path.isdir(file):
                meta_hash = hashlib.sha1(str(os.stat(file)).encode('utf-8'))
                dbupdate.append(f"path:{file};sha1:;stat:{meta_hash.hexdigest()}")
        except Exception as e:
            syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR] {e}")
    return dbupdate

def removeNewLine(lines):
    return [*map(lambda s: s.replace("\n", ""), lines)]

def getListOfFiles(dirNames):
    dirNames = dirNames.split(",")
    allFiles = list()
    listOfFile = list()
    for dir in dirNames:
        if dir:
            if not os.path.exists(dir):
                syslog.syslog(syslog.LOG_CRIT, f"pyfim-[ERROR] Dir not found:{dir}, Dir deleted or check Config")
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
                if fullPath not in path_ignore and '\\' not in fullPath:
                    # If entry is a directory then get the list of files in this directory
                    if os.path.isdir(fullPath):
                        allFiles = allFiles + getListOfFiles(fullPath)
                    else:
                        allFiles.append(fullPath)
                else:
                    continue
    return allFiles

def writeDB(dbupdate):
    dbupdatewnewline = ["{}\n".format(i) for i in dbupdate]
    with open('./pyfim.db', 'w') as f:
        f.writelines(dbupdatewnewline)

def compareAndUpdateDB(dbupdate):
    dbcompare = list()
    tag = str()
    with open("./pyfim.db", "r") as f:
        for line in f:
            dbcompare.append(line.strip("\n"))
    if dbcompare == dbupdate:
        return None
    sdc = set(dbcompare)
    diffModAdd = [x for x in dbupdate if x not in sdc]

    sdu = set(dbupdate)
    diffsDel = [x for x in dbcompare if x not in sdu]
    if not diffsDel and not diffModAdd:
        return None
    if diffModAdd:
        sizediffsmodadd = len(diffModAdd)
        for i in range(sizediffsmodadd):
            entry = diffModAdd[i]
            parts = entry.split(";")
            pathformodcheck = "%s;" % (parts[0])
            if [True for s in diffsDel if pathformodcheck in s]:
                # modified
                entrysplit = entry.split(";")
                file = parts[0].replace('path:', '')
                oldFileHash = entrysplit[1].replace("sha1:", "")
                newFileHash = parts[1].replace("sha1:", "")
                oldStatHash = entrysplit[2].replace("stat:", "")
                newStatHash = parts[2].replace("stat:", "")
                if not oldStatHash and oldFileHash != newFileHash:
                    tag = "[FILE]"
                elif not oldFileHash and oldStatHash != newStatHash:
                    tag = "[DIR]"
                else:
                    tag = "[FILE,META]"
                syslog.syslog(syslog.LOG_CRIT,
                              f"pyfim-{tag} Modified:{file}, Old-File-Hash:{oldFileHash}, New-File-Hash:{newFileHash}, Old-Meta-Hash:{oldStatHash}, New-Meta-Hash:{newStatHash}")
            else:
                # added
                file = parts[0].replace('path:', '')
                newFileHash = parts[1].replace("sha1:", "")
                newStatHash = parts[2].replace("stat:", "")
                if newFileHash and not newStatHash:
                    tag = "[FILE]"
                elif not newFileHash and os.path.isdir(file):
                    tag = "[DIR]"
                else:
                    tag = "[FILE,META]"
                syslog.syslog(syslog.LOG_CRIT,
                              f"pyfim-{tag} Added:{file}, File-Hash:{newFileHash}, Meta-Hash:{newStatHash}")
    if diffsDel:
        sizediffsdel = len(diffsDel)
        for i in range(sizediffsdel):
            entry = diffsDel[i]
            parts = entry.split(";")
            pathfordelcheck = "%s;" % (parts[0])
            if not [s for s in diffModAdd if pathfordelcheck in s]:
                file = parts[0].replace('path:', '')
                FileHash = parts[1].replace("sha1:", "")
                StatHash = parts[2].replace("stat:", "")
                if FileHash and not StatHash:
                    tag = "[FILE]"
                elif not FileHash and StatHash and os.path.isdir(file):
                    tag = "[DIR]"
                else:
                    tag = "[FILE,META]"
                syslog.syslog(syslog.LOG_CRIT,
                              f"pyfim-{tag} Deleted:{file}, File-Hash:{FileHash}, Meta-Hash:{StatHash}")
    return dbupdate


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

path_meta_files = getListOfFiles(path_meta)
path_norm_files = getListOfFiles(path_norm)

calcHashNorm(path_norm_files, dbupdate)
calcHashMeta(path_meta_files, dbupdate)

if os.path.exists("./pyfim.db") and os.path.getsize("./pyfim.db") > 0:
    compareAndUpdateDB(dbupdate)
    syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Update Database")
    writeDB(dbupdate)
else:
    syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Create Database")
    writeDB(dbupdate)

syslog.syslog(syslog.LOG_WARNING, f"pyfim-[END] Scan took:{round((time.time() - start_time), 5)} Sec")
sys.exit(1)
