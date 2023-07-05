import os
import re
import struct
import mmap
import win32api
import json
from threading import Lock

def AHKType(exeName, Unicode=True):
    Type = {}

    # Get file version
    vert = 0
    try:
        info = getFileProperties(exeName)
        Type["FileVersion"] = info["FileVersion"]
        Type["FileDescription"] = info["StringFileInfo"]["FileDescription"]
        vert = info['FileVersion']
    except OSError:
        pass

    if not vert:
        return False
    
    vert = vert.split('.')
    vert = int(vert[3]) | (int(vert[2]) << 8) | (int(vert[1]) << 16) | (int(vert[0]) << 24)
    # We're dealing with a legacy version if it's prior to v1.1
    Type['Era'] = "Modern" if vert >= 0x01010000 else "Legacy"


    if Unicode:
        try:
            with open(exeName, 'rb') as f:
                exeData = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                
                exeMachine = struct.unpack_from("H", exeData, struct.unpack_from("I", exeData, 60)[0] + 4)[0]
                Type['PtrSize'] = {0x8664: 8, 0x014C: 4}.get(exeMachine, 0)
                if not Type['PtrSize']:
                    return Type  # Not a valid exe (or belongs to an unsupported platform)
                
                Type['IsUnicode'] = bool(re.search(b'MsgBox\x00', exeData))
                Type['Summary'] = 'U64' if Type['PtrSize'] == 8 else 'U32' if Type['IsUnicode'] else 'A32'
        except OSError:
            pass
    return Type



class AHKFinder:
    def __init__(self):
        self.variants = []
        self.__find_ahks(os.path.join(os.path.dirname(os.path.realpath(__file__)), "bin"))
        self.variants = sorted(self.variants, key=lambda x: x['version'])
    
    def has(self, variant):
        for value in self.variants:
            if value['version'] == variant:
                return True
        return False
    
    def get(self, variant):
        for value in self.variants:
            if value['version'] == variant:
                return value
        return False

    def __find_ahks(self, file_name):
        for root, dirs, files in os.walk(file_name):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                type_info = AHKType(file_path)
                if type_info['Era'] == "Modern" and (file_name.endswith(".bin") or (file_name.endswith(".exe") and "FileDescription" in type_info and "AutoHotkey" in type_info['FileDescription'])):
                    version = type_info['FileVersion'] + " " + type_info['FileDescription']
                    if file_name.endswith(".exe") or file_name.endswith(".bin"):
                        if self.has(version):
                            continue
                        # https://github.com/AutoHotkey/Ahk2Exe/issues/98
                        # wk = re.split(r"\.|-", type_info['FileVersion'])
                        # if not ((wk[0] == "1" and int(wk[2]) >= 34) or (wk[0] == "2" and (int(wk[2]) >= 3 or int(wk[2]) >= int("135")))):
                        #     continue
                        print(type_info)
                        display_name = re.sub(r'\s+', ' ', f"v{type_info['FileVersion']} {type_info['Summary']} {type_info['FileDescription']} " + (file_name if "AutoHotkey" not in type_info['FileDescription'] else ""))
                        if "AutoHotkey" not in type_info['FileDescription']:
                            display_name =  ".".join(display_name.split('.')[:-1])
                        print(display_name)
                        variant = {
                            "version": version,
                            "file": file_path,
                            "display_name": display_name or ""
                        }
                        self.variants.append(variant)

class Config:
    def __init__(self, config_name="config.json"):
        # Define a lock to ensure thread safety during file update
        self.__config_lock = Lock()
        self.config_name = config_name
        with self.__config_lock:
            if os.path.exists(os.path.join(config_name)):
                with open(self.config_name, 'r') as config_file:
                    self.data = json.load(config_file)
            else:
                self.data = None

    # Function to update the configuration file
    def __update(self):
        with self.__config_lock:
            with open(self.config_name, 'w') as config_file:
                json.dump(self.data, config_file, indent=4)
                
    def update_compile_count(self, new_number):
        with self.__config_lock:
            self.data['compile']['count'] = new_number
        self.__update()



#==============================================================================
def getFileProperties(fname):
#==============================================================================
    """
    Read all properties of the given file return them as a dictionary.
    """
    propNames = ('Comments', 'InternalName', 'ProductName',
        'CompanyName', 'LegalCopyright', 'ProductVersion',
        'FileDescription', 'LegalTrademarks', 'PrivateBuild',
        'FileVersion', 'OriginalFilename', 'SpecialBuild')

    props = {'FixedFileInfo': None, 'StringFileInfo': None, 'FileVersion': None}

    try:
        # backslash as parm returns dictionary of numeric info corresponding to VS_FIXEDFILEINFO struc
        fixedInfo = win32api.GetFileVersionInfo(fname, '\\')
        props['FixedFileInfo'] = fixedInfo
        props['FileVersion'] = "%d.%d.%d.%d" % (fixedInfo['FileVersionMS'] / 65536,
                fixedInfo['FileVersionMS'] % 65536, fixedInfo['FileVersionLS'] / 65536,
                fixedInfo['FileVersionLS'] % 65536)

        # \VarFileInfo\Translation returns list of available (language, codepage)
        # pairs that can be used to retreive string info. We are using only the first pair.
        lang, codepage = win32api.GetFileVersionInfo(fname, '\\VarFileInfo\\Translation')[0]

        # any other must be of the form \StringfileInfo\%04X%04X\parm_name, middle
        # two are language/codepage pair returned from above

        strInfo = {}
        for propName in propNames:
            strInfoPath = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, propName)
            ## print str_info
            strInfo[propName] = win32api.GetFileVersionInfo(fname, strInfoPath)

        props['StringFileInfo'] = strInfo
    except:
        pass

    return props
