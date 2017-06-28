
import idaapi, idc, idautils
import os
from IdaSync.IdaTypeStorage import Storage_sqlite, LocalType, IdaTypeStringParser, ConnectToSQLBase,ChooseProject
import pickle

fDebug = False
if fDebug:
    import pydevd




class GlobalType(LocalType):

    def __init__(self, name = "", TypeString = "",  TypeFields = "", addr = idaapi.BADADDR):
        super(GlobalType,self).__init__(name, TypeString, TypeFields)
        self.addr = addr

    def to_dict(self):
        ser_dic = {}
        ser_dic['name'] = self.name
        ser_dic['TypeString'] = self.TypeString.encode("base64")
        ser_dic['TypeFields'] = self.TypeFields.encode("base64")
        ser_dic['addr'] = self.addr
        ser_dic['parsedList'] = self.parsedList
        ser_dic['depends'] = self.depends
        ser_dic['depends_ordinals'] = self.depends_ordinals
        return ser_dic

    def from_dict(self,ser_dic):
        self.name = ser_dic['name'].encode("ascii")
        self.TypeString = ser_dic['TypeString'].encode("ascii").decode("base64")
        self.TypeFields = ser_dic['TypeFields'].encode("ascii").decode("base64")
        self.addr = ser_dic['addr']
        self.parsedList = ser_dic['parsedList']
        self.depends = ser_dic['depends']
        self.depends_ordinals = ser_dic['depends_ordinals']
        return self

    def print_type(self):
        ret = idaapi.idc_print_type(self.GetTypeString(),self.TypeFields,self.name,idaapi.PRTYPE_MULTI|idaapi.PRTYPE_TYPE)
        if ret is None:
            return ""
        i = 0
        ret = ret.strip()
        return ret



class IdaSyncSqliteStorage(Storage_sqlite):

    def __init__(self, db_name, project_name=""):
        super(IdaSyncSqliteStorage,self).__init__(db_name,project_name)
        if self.project_name != "":
            self.project_globals_name = "%s_globals" % self.project_name
            if self.isProjectGlobalsExist(self.project_globals_name):
                self.request(
                    "CREATE TABLE %s (name text, TypeString text, TypeFields text, addr text, parsedList text, depends text, depends_ordinals text)" % (
                    self.project_globals_name))

    def isProjectGlobalsExist(self,name=""):
        return  True if len(self.request("SELECT name FROM sqlite_master WHERE type='table' AND name=?;",(self.project_globals_name if name == "" else name,))) == 1 else False


    def connect(self,project_name):
        super(IdaSyncSqliteStorage,self).connect(project_name)
        if self.project_name != "":
            self.project_globals_name = "%s_globals" % self.project_name
            if self.isProjectGlobalsExist(self.project_globals_name):
                self.request(
                    "CREATE TABLE %s (name text, TypeString text, TypeFields text, addr text, parsedList text, depends text, depends_ordinals text)" % (
                    self.project_globals_name))

    def GetAllProjects(self):
        ret = []
        for pr in super(IdaSyncSqliteStorage,self):
            if pr[-len("_globals"):] != "_globals":
                ret.append(pr)
        return ret

    def GetAllGlobalsNames(self):
        return self.modify_ret(self.request("SELECT name FROM %s"%(self.project_globals_name)))

    def to_dict(self,res):
        ser_dic = {}
        ser_dic['name'] = res[0]
        ser_dic['TypeString'] = res[1]
        ser_dic['TypeFields'] = res[2]
        ser_dic['addr'] = pickle.loads(res[3].encode("ascii").decode("base64"))
        ser_dic['parsedList'] = pickle.loads(res[4].encode("ascii").decode("base64"))
        ser_dic['depends'] = pickle.loads(res[5].encode("ascii").decode("base64"))
        ser_dic['depends_ordinals'] = pickle.loads(res[6].encode("ascii").decode("base64"))
        return ser_dic

    def putGlobalToStorage(self,t):
        ser_dic = t.to_dict()
        try:
            self.request("INSERT INTO %s VALUES (?, ?, ?, ?, ?, ?, ?)"%(self.project_globals_name),(ser_dic['name'],ser_dic['TypeString'],ser_dic['TypeFields'],pickle.dumps(ser_dic["addr"]).encode("base64"),pickle.dumps(ser_dic["parsedList"]).encode("base64"),pickle.dumps(ser_dic["depends"]).encode("base64"),pickle.dumps(ser_dic["depends_ordinals"]).encode("base64")))
        except:
            Warning("Exception on sqlite putToStorage")

    def getGlobalFromStorage(self,name):
        res = []
        try:
            res = self.request("SELECT * FROM %s WHERE name=?"%(self.project_globals_name),(name,))
            if len(res) == 0:
                return None
            elif len(res) > 1:
                raise NameError("getFromStorage: Type duplication or error. Count = %d" % len(res))
            else:
                return GlobalType().from_dict(self.to_dict(res[0]))
        except:
            Warning("Exception on sqlite getFromStorage")
            return None

    def isGlobalExist(self,name):
        res = self.request("SELECT * FROM %s WHERE name=?"%(self.project_globals_name), (name,))
        if len(res) == 0:
            return False
        elif len(res) == 1:
            return True
        else:
            raise NameError("isExist: Type duplication or error. Count = %d" % (len(res)))

    def updateGlobalType(self,name,t):
        ser_dic = t.to_dict()
        try:
            self.request("UPDATE %s SET name = ?, TypeString = ?, TypeFields = ?, addr = ?, parsedList = ?, depends = ?, depends_ordinals = ? WHERE name = ?"%(self.project_globals_name), (ser_dic['name'], ser_dic['TypeString'], ser_dic['TypeFields'], pickle.dumps(ser_dic["addr"]).encode("base64"),
                                                                                pickle.dumps(ser_dic["parsedList"]).encode("base64"), pickle.dumps(ser_dic["depends"]).encode("base64"),
                                                                                pickle.dumps(ser_dic["depends_ordinals"]).encode("base64"),name))
            return True
        except:
            Warning("Exception on sqlite updateType")
            return False

    def deleteProject(self,name = ""):
        super(IdaSyncSqliteStorage,self).deleteProject(name)
        if name == "":
            name = self.project_globals_name
        self.request("drop table %s"%(name))


class IdaSync(object):

    def __init__(self):
        self.type_storage = IdaTypeStringParser()
        self.Globals = {}
        self.storage = None
        pass

    def ConnectToStorage(self):
        self.type_storage.storageAddr = os.path.join(idc.GetIdaDirectory(),"IdaSync.db")
        db = IdaSyncSqliteStorage(os.path.join(idc.GetIdaDirectory(),"IdaSync.db"))
        db.connect(idc.GetInputFile())
        self.type_storage.storage = db
        self.storage = db
        return True

    def doPushAll(self):
        if fDebug ==True:
            pydevd.settrace('127.0.0.1', port=31337, stdoutToServer=True, stderrToServer=True, suspend=False)

        if self.type_storage.storage is None:
            if not self.ConnectToStorage():
                return
        self.type_storage.Initialise()
        # sorted_list = self.type_storage.resolveDependenciesForExport(self.LocalTypeMap.values())
        self.type_storage.saveToStorage(self.type_storage.LocalTypeMap.values(), True)

        self.Initialise()
        self.saveGlobalsToStorage(self.Globals.values(),True)

    def doPullAll(self):
        if fDebug ==True:
            pydevd.settrace('127.0.0.1', port=31337, stdoutToServer=True, stderrToServer=True, suspend=False)

        if self.type_storage.storage is None:
            if not self.ConnectToStorage():
                return

        self.type_storage.doPullAll()
        self.Initialise()
        self.getGlobalsFromStorage(self.storage.GetAllGlobalsNames())


    def Initialise(self):
        self.Globals = {}
        for addr, n in idautils.Names():
            ts = idc.GetTinfo(addr)
            if ts is None:
                if idc.GuessType(addr) is not None:
                    idc.SetType(addr,idc.GuessType(addr))
                    ts = idc.GetTinfo(addr)
                else:
                    ts = ["",""]
            self.Globals[n] = GlobalType(n, ts[0], ts[1], addr)

    def saveGlobalsToStorage(self,typesList,fReplace = False):
        for t in typesList:
            if self.storage.isGlobalExist(t.name):
                tp = self.getGlobalsFromStorage([t.name])[0]
                if not t.isEqual(tp):
                    if fReplace:
                        t1 = t
                        self.storage.updateGlobalType(t1.name, t1)
                    else:
                        t1 = self.DuplicateResolver(tp,t,True)
                        if not tp.isEqual(t1):
                            self.storage.updateGlobalType(t1.name,t1)
                        #self.cachedStorage[t1.name] = t1
                        #print "Edited type updated"
                    # raise NameError("saveToStorage: Duplicated type name (%s) with differ body"%t.name)
                continue
            self.storage.putGlobalToStorage(t)
            #self.cachedStorage[t.name] = t

    def getGlobalsFromStorage(self,typesListNames):
        typesList = []
        for name in typesListNames:
            t = self.storage.getGlobalFromStorage(name)
            if t is None:
                raise NameError("getFromStorage: Type name (%s) not in the storage"%name)
            typesList.append(t)
            #self.cachedStorage[name] = t
        return typesList

    def setGlobal(self,global_type, fReplace=False):
        if global_type.name in self.Globals:
            local_global = self.Globals[global_type.name]

            if local_global.addr == global_type.addr:
                if not global_type.isEqual(local_global):
                    if fReplace:
                        idaapi.set_name(global_type.addr, global_type.name)
                        idc.ApplyType(global_type.addr,(global_type.name, global_type.GetTypeString(), global_type.TypeFields))
                    else:
                        global_type = self.DuplicateResolver(local_global, global_type)
                        idaapi.set_name(global_type.addr, global_type.name)
                        idc.ApplyType(global_type.addr,(global_type.name, global_type.GetTypeString(), global_type.TypeFields))

        else:
            idaapi.set_name(global_type.addr, global_type.name)
            idc.ApplyType(global_type.addr, (global_type.name, global_type.GetTypeString(), global_type.TypeFields))




    def DuplicateResolver(self, t1, t2, fToStorage=False):
        return t1