'''jsconvert/pyrules/polyfills.py

Provides code rules for transpiling JS String methods to Pyhon source code. These 
rules typically modify one or more components in a significant way.  The rules 
may even choose to add or import new scripts to the source transpiling.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on May 30, 2022

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

from jsconvert.transpiler import CodeRule
from jsconvert.comp import Expression, VariableType, StringType
from .polyfills import RefactorFunc

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["FromCharCodeFill", "CharCodeFill", "CharAtFill", "SubstringFill", "LocaleCompareFill",
    "RefactorStringFunc"
    ]

    
class FromCharCodeFill(CodeRule):
    def __init__(self):
        super().__init__("from-charcode-fill", ["GlobalType", "Function", "NameType"])
          
    def apply(self, b, offset):
        if b.current().name == "String" and b.next().name == "fromCharCode":
            b.add("chr")
            return 3
        
        return 0
    
    
class CharCodeFill(CodeRule):
    def __init__(self):
        super().__init__("charCodeAt-fill", ["Function", "ANY", "FunctionEnd"])
          
    def apply(self, b, offset):
        if b.next().name != "charCodeAt" or not b.current().is_nested():
            return 0
        
        if b.insert_prefix("ord(", {"this": "self"}):
            if b.peek() == ".":
                b.buf.pop()
                
            sb = b.get_sub_buffer(b.current())
            sb.entries = sb.entries[2:sb.size-1]
            sb.size -= 3
            b.add("["+"".join(sb.transpile()).rstrip()+"]")
            return  offset
        
        return 0

    
class CharAtFill(CodeRule):
    def __init__(self):
        super().__init__("charAt-fill", ["Function", "ANY", "FunctionEnd"])
    
    def apply(self, b, offset):
        if b.next().name != "charAt" or not b.current().is_nested():
            return 0
        
        sb = b.get_sub_buffer(b.current())
        sb.entries = sb.entries[2:sb.size-1]
        sb.size -= 3
        
        b.buf.pop()
        b.add("["+"".join(sb.transpile()).rstrip()+"]")
        b.add(b.current(offset).extended and "." or " ")
        return offset+1
    
              
    

class SubstringFill(CodeRule):
    def __init__(self):
        super().__init__("substring-fill", ["Function", "NameType", "Begin", "Expression", "ANY", "FunctionEnd"])
        
    def apply(self, b, offset):
        c = b.current()
        if (c.name != "substring" or
            not c.is_nested() or 
            not isinstance(b.current(3), Expression)):
            return 0
        
        if b.peek() == ".":
            b.buf.pop()
            
        b.add("[")
        
        ch = b.current().get_children()
        b.append_buffer(b.get_sub_buffer(ch[2]))
        b.trim()
        b.add(":")
        
        if ch[3].name == ",":
            b.append_buffer(b.get_sub_buffer(ch[4]))
            b.trim()
            
        b.add("]")
        b.add(b.current(offset).extended and "." or " ")
                    
        return offset+1
    
   
class LocaleCompareFill(CodeRule):
    """string.localeCompare(seg) -> strcoll(string, seg) 
        
        May add Import locale.strcoll  (string collate)
    """
    
    def __init__(self):
        super().__init__("locale-compare-fill", ["Function", "NameType", "Begin", "Expression"])
        
    def apply(self, b, offset):
        c = b.current()
        if c.name != "localeCompare" or not c.is_nested():
            return 0
        
        v = b.current(4)
        if type(v) is not VariableType and type(v) is not StringType:
            return 0
        
        if b.insert_prefix("strcoll(", {"this": "self"}):
            if b.peek() == ".":
                b.buf.pop()
                
            if not b.import_map.is_imported("strcoll"):
                b.insert_import_statement("import {strcoll} from 'locale';")
            
            b.add(", ")  
            offset = b.append_buffer(b.get_sub_buffer(b.current(3))) + 4
            b.trim()
            return offset
        
        return 0

class IndexOfFill(CodeRule):
    def __init__(self):

        super().__init__("indexOf-fill", ["Function", "NameType", "Begin", "Expression", "StringType"])
        
    def apply(self, b, offset):
        if b.current().name == "indexOf" and b.current().is_nested():
            b.add("find")
            return 2 
        
        return 0   

class RefactorStringFunc(RefactorFunc):
    
    factors = {
        "startsWith": "startswith",
        "endsWith": "endswith",
        "trim": "strip",
        "indexOf": "find",
        "lastIndexOf": "rfind"
        }
    
    nested = True
    
    def __init__(self):
        super().__init__("refactor-string-functions")
        

 
