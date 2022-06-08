'''jsconvert/__main__.py

This module supports the transpiling of javascript (ES6) source code into Python
and other Languages from a command line interface.

The interface provides an input prompt requesting a javascript file or directory;
an output file (optional); the name of a rule module (optional); and asks if a
document object model (DOM) should also be output (optional)

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on June 7, 2022

Copyright 2022 Jon L. Boynton

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
'''

from .transpiler import convert
from pathlib import Path
from sys import exit

def _yes(msg):
    return msg.lower() in ("y", "yes", "true", "1")


if __name__ == '__main__':
    print("_________________________________________________\n"+
        "Welcome to JSConvert - CLI  v1.0.1\n\n"+
        "Author: Jon L. Boynton\n"+
        "Copyright 2022 Jon L. Boynton\n"+
        "Licensed under the Apache License, Version 2.0\n"+
        "_________________________________________________\n")
    
    stop = False
    
    while not stop:
        try:
            msg = input("Enter a JS file or directory:\n")
            filein = str(Path().absolute().joinpath(msg).resolve())
            fileout = None
            rules = "jsconvert.pyrules"
            
            msg = input("Change output file? (Y/N):")
            
            if _yes(msg):
                msg = input("Enter a Python output directory:\n")
                fileout = str(Path().absolute().joinpath(msg).resolve())
                
            msg = input("Change conversion rules? (Y/N):")
            
            if _yes(msg):
                rules = input("Enter a rule module:\n")
                
            msg = input("Create DOM Files? (Y/N):")
                
            convert(filein, fileout, rules, _yes(msg))
                
           
        except Exception as err:
            print(str(err))
            
        if _yes(input("Continue? (Y/N):")):
            continue
        
        stop = True
    
    exit(0)