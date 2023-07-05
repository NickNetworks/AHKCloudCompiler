from datetime import datetime
import os
import random
import string
import subprocess
import time
import shutil
import platform
import hashlib

# Command Line Parameters:
# A_ScriptName [/in infile.ahk] [/out outfile.exe] [/icon iconfile.ico] [/base AutoHotkeySC.bin] [/resourceid #1] [/compress 0|1|2] [/cp codepage] [/silent] [/gui]
# A_ScriptName: The name of the script being executed.
# /in infile.ahk: Specifies the input AHK (AutoHotkey) file to be compiled.
# /out outfile.exe: Specifies the output EXE (executable) file name.
# /icon iconfile.ico: Specifies the icon file to be embedded in the EXE file.
# /base AutoHotkeySC.bin: Specifies the base file for the compilation.
# /resourceid #1: Specifies the resource ID for the compiled script.
# /compress 0|1|2: Specifies the compression level for the compiled EXE. Use 0 for no compression, 1 for MPRESS compression, and 2 for UPX compression.
# /cp codepage: Specifies the codepage to be used for compilation.
# /silent: Runs the compilation process silently without displaying output. Optionally, /verbose can be added to display verbose output.
# /gui: Forces the script to use a GUI (Graphical User Interface) when compiling.


# AutoHotkey has three main versions: 1.0, 1.1, and 2.0. The last 1.0 version, 1.0.48.05, 
# used its own Ahk2Exe compiler, distinct from the current v1.1 and 2.0 Ahk2Exe.
# AHK 1.1 and 2.0 have enhancements, from versions 1.1.34.00 and 2.0-a135 respectively,
# to use AutoHotkey*.exe files as base files for compilation, while older versions only
# used *.bin files. The latest Ahk2Exe v1.1 is capable of compiling all 
# v1.1.xx.xx and v2.xx.xx.xx scripts and is usually the most bug-free

class Compiler:
    def __init__(self, ahk, config):
        self.batch = None
        self.ahk = ahk
        self.config = config
        for directory in ["tmp", "output"]:
            # Check if the directory does not exist
            if not os.path.exists(directory):
                # If it doesn't exist, create it
                os.makedirs(directory)

    def batch(self, line):
        if self.batch is None:
            self.batch = []
        self.batch.append(line + "\r\n")

    def compile(self, text, compress, variant=None, resourceid = None, codepage = None):
        if text is None and self.batch is not None:
            text = "".join(self.batch)
            self.batch = None
        resourceid = None if resourceid and len(resourceid) == 0 else resourceid
        if variant:
            my_variant = self.ahk.get(variant)
        else:
            my_variant = None;


        # Calculate the total source size
        total_source_size = len(text)

        # Get the current time and date
        current_time = datetime.now()
        current_day = current_time.day
        current_month = current_time.strftime("%B")
        current_year = current_time.year
        compile_count = self.config.data['compile']['count']
        match int(compress):
            case 1:
                compression = "MPRESS"    
            case 2:
                compression = "UPX"
            case _:
                compression = "None"
        print(my_variant)
        dest_name = f"CloudAHK-"
        if self.config.data['compile']['cache']:
            md5 = hashlib.md5(bytes(text, "utf-8")).hexdigest()
            dest_name += md5
        else:
             + ''.join(random.choice(string.ascii_letters) for _ in range(10))
        # Store the output in a variable
        text = f"""A_CloudCompile := \"
(
Compiliation Time: {current_time:%H:%M:%S} {current_month}/{current_day}/{current_year}
AHK Variant: {variant}
Codepage: {codepage} Resource ID: {resourceid}
Compression Type: {compression}
Compilation Number: {compile_count}
Total Source Size: {total_source_size} bytes
)\"
{text}
"""
        
        self.config.update_compile_count(compile_count+1)

        tmp = os.path.join("tmp", dest_name + ".tmp")
        tmp_done = os.path.join("tmp", dest_name + ".exe")
        out = os.path.join("output", dest_name + ".exe")
        if self.config.data['compile']['cache'] and os.path.exists(out):
            print(f"Caching enabled, and {out} exists, don't compile and serve it")
            return out, None
        with open(tmp, 'w') as f:
            f.write(text)

        command = [
            os.path.join("bin", "Ahk2Exe.exe"),
            "/in",
            tmp,
            "/icon",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
            "/compress",
            compress,
            "/silent",
            "verbose"
        ]

        if my_variant:
            command.append("/base")
            command.append(my_variant['file'])

        if resourceid:
            command.append("/resourceid")
            command.append(resourceid)
        if resourceid:
            command.append("/cp")
            command.append(codepage)

        if platform.system() != 'Windows':
            # If we're on a Linux or other system 
            command.insert(0, "wineconsole")
            os.environ["DISPLAY"] = ":0.0"
        print(f"Building with command {' '.join(command)}")
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=".")
        output, err = proc.communicate()
        # if output:
        #     print(output)
        if "Ahk2Exe Error" in output.decode('utf-8'):
            print("compile error")
            os.remove(tmp)
            return False, output
        
        if err:
            os.remove(tmp)
            return False, err
        
        shutil.move(tmp_done, out)
        os.remove(tmp)
        return out, None
