import os
import sys
import syslog
import xml.etree.ElementTree as tree
import time
import cpyfim

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

    path_meta_files = getListOfFiles(path_meta)
    path_norm_files = getListOfFiles(path_norm)

    cpyfim.calcHashNorm(path_norm_files, dbupdate)
    cpyfim.calcHashMeta(path_meta_files, dbupdate)

    if os.path.exists("./pyfim.db") and os.path.getsize("./pyfim.db") > 0:
        cpyfim.compareAndUpdateDB(dbupdate)
        syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Update Database")
        cpyfim.writeDB(dbupdate)
    else:
        syslog.syslog(syslog.LOG_WARNING, "pyfim-[INIT] Create Database")
        cpyfim.writeDB(dbupdate)

    syslog.syslog(syslog.LOG_WARNING, f"pyfim-[END] Scan took:{round((time.time() - start_time), 5)} Sec")
    sys.exit(1)
