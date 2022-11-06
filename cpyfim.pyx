#cython: profile=True
import hashlib
import os
import syslog

cpdef writeDB(dbupdate):
    cdef int sizedbupdate
    cdef str i
    cdef str line
    cdef list dbupdatewnewline
    dbupdatewnewline = ["{}\n".format(i) for i in dbupdate]
    with open('./pyfim.db', 'w') as f:
        f.writelines(dbupdatewnewline)

cpdef compareAndUpdateDB(dbupdate):
    cdef dbcompare = list()
    cdef str diffforgrep = "./out"
    cdef str file, oldFileHash, newFileHash, oldStatHash, newStatHash,tag = ""
    with open("./pyfim.db", "r") as f:
        for line in f:
            dbcompare.append(line.strip("\n"))
    if dbcompare == dbupdate:
        return None
    cdef int sizediffsmodadd
    cdef int sizediffsdel
    cdef str entry
    cdef list diffModAdd = list()
    cdef list diffsDel = list()
    cdef set s
    cdef int i
    cdef list parts = list()
    cdef str pathformodcheck
    cdef str pathfordelcheck
    s = set(dbcompare)
    diffModAdd = [x for x in dbupdate if x not in s]

    s = set(dbupdate)
    diffsDel= [x for x in dbcompare if x not in s]

    if not diffsDel and not diffModAdd:
        return None
    if diffModAdd:
        sizediffsmodadd = len(diffModAdd)
        for i in range(sizediffsmodadd):
            entry = diffModAdd[i]
            parts = entry.split(";")
            pathformodcheck = "%s;" % (parts[0])
            if [True for s in dbcompare if pathformodcheck in s]:
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
            if [True for s in dbupdate if pathfordelcheck in s]:
                continue
            else:
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

def  calcHashNorm(path_norm_files, dbupdate):
    for i in range(len(path_norm_files)):
        try:
            file = path_norm_files[i]
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

def  calcHashMeta(path_meta_files, dbupdate):
    #cdef str meta_hash = ""
    for i in range(len(path_meta_files)):
        try:
            file = path_meta_files[i]
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