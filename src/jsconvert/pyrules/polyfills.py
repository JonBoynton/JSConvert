'''jsconvert/pyrules/polyfills.py

Provides code rules for sophisticated transpiling of jsconvert DOM components
into Python source code.  These rules typically modify one or more components in
a significant way.  The rules may even choose to add or import new scripts to
the source transpiling.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Nov 28, 2021

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
from jsconvert.comp import RootEntry, VariableType, StringType, NumberType, Classs
from jsconvert.lang import KW_switch

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["TrueFill", "FalseFill", "TypeFill", "InstanceFill", "InstanceGlobalFill",
     "ToStringFill", "AddStrDefFill", "LengthFill", "LengthThisFill", "SwitchFill", 
     "CaseFill", "DefaultCaseFill", "LabelBreakFill", "PromiseCatchFill", "SingletonFill", 
     "MapHasFill", "RefactorMisc", "DateNowFill", "JSONStringifyFill", "RefactorBuiltins", 
     "RefactorNewInstance", "UndefinedFill"
    ]



class TrueFill(CodeRule):
    def __init__(self):
        super().__init__("true-fill", ["KW_true"])
        
    def apply(self, buffer, offset):
        buffer.add("True")
        return 1

    
class FalseFill(CodeRule):
    def __init__(self):
        super().__init__("false-fill", ["KW_false"])
        
    def apply(self, buffer, offset):
        buffer.add("False")
        return 1

    
class TypeFill(CodeRule):
    def __init__(self):
        super().__init__("type-fill", ["KW_typeof", "VariableType", "Compare", "StringType"])
        
    def apply(self, b, offset):
        typ = b.current(offset).value_of()
        spec = "type("+b.next().name+").__name__ "
        op = b.current(2).name
        if len(op) > 2:
            op = op[:2]
        
        if typ == "string":
            spec += op+" 'str'"
        elif typ == "boolean":
            spec += op+" 'bool'"
        elif typ == "function":
            spec += op+" 'function'"
        elif typ == 'number':
            spec = "(("+spec+"== 'float' or "+spec+"== 'int') and 'number' or '') "+op+" 'number'"
        elif typ == 'bigint':
            spec += op+" 'int'"
        else:
            spec = "(("+spec+"not in {'str','float','int','bool','function'}) and 'object' or '') "+op+" 'object'"
        
        b.add(spec)
        return 4

    
class InstanceFill(CodeRule):
    def __init__(self, name=None, path=None):
        super().__init__(name or "instance-fill", path or ["VariableType", "KW_instanceof", "VariableType"])
        
    def apply(self, b, offset):
        if b.insert_prefix("isinstance(", {"this": "self"}):
            b.add(b.current().name+", "+b.current(2).name+")")
            return 3
        
        return 0
    
class InstanceGlobalFill(InstanceFill):
    def __init__(self):
        super().__init__("instance-global-fill", ["VariableType", "KW_instanceof", "GlobalType"])
        
        
class ToStringFill(CodeRule):
    def __init__(self):
        super().__init__("toString-fill", ["Function", "NameType", "Begin", "FunctionEnd"])
           
    def apply(self, b, offset):
        if b.next().name != "toString" or not b.current().is_nested():
            return 0
        
        if b.insert_prefix("str(", {"this": "self"}):
            b.add(")")
            b.add(b.current(offset).extended and "." or " ")
            return 4
        
        return 0

class AddStrDefFill(CodeRule):
        
    def __init__(self, name=None):
        super().__init__(name or "add-str-definition-fill", ["Method", "Declaration", "Constructor", "Begin", "End"])
        
    def apply(self, b, offset):
        if b.current().value == "toString":
            c = b.current().par.par
            
            if c and c.par and isinstance(c.par, Classs):
                b.new_line()
                sb = []
                sb.append("def __str__(self):")
                sb.append("\n"+b.indent(1))
                sb.append("return self.toString()")
                sb.append("\n"+b.indent())
                b.insert_code("".join(sb))
            
        return 0 
    
              
class LengthFill(CodeRule):
    def __init__(self, name=None, path=None):
        super().__init__(name or "length-fill", path or ["Assignment", "Operator", "Expression", "VariableType", "VariableType"])
                
    def apply(self, b, offset):
        c = b.current(offset)
        if c.name == "length" and not c.extended and b.next().name in ("=", "+=", "-=", "*=" "/=", "%="):
            b.space()
            b.add(b.next().name)
            b.space()
            b.add("len(")
            fn = b.current(offset-1).get_full_name()
            b.add(fn[:len(fn) - 7])
            b.add(")")            
            return offset+1
        
        return 0
    
class LengthThisFill(LengthFill):
    def __init__(self, name=None, path=None):
        super().__init__("length-this-fill", ["Assignment", "Operator", "Expression", "KW_this", "VariableType", "VariableType"])
    
   
class SwitchFill(CodeRule):
    def __init__(self):
        super().__init__("switch-fill", ["KW_switch", "Expression", "ANY", "ExpressionEnd"])
           
    def apply(self, b, offset):
        ex = b.get_sub_buffer(b.next())
        ex.entries = ex.entries[1: ex.size - 1]
        ex.size -= 2
        
        
        b.new_line()
        v = "_switch_"+str(b.offset)
        b.add(v)
        b.add(" = " + "".join(ex.transpile()))
        b.new_line()
        b.add("while True")

        return offset+1
    
       
class CaseFill(CodeRule):
    def __init__(self):
        super().__init__("case-fill", ["KW_case", "ANY", "End"])
        
    def apply(self, b, offset):
        c = b.current() 
        
        key = None
        falls = False
        for k in reversed(b.buf):
            if k.startswith("_switch_"):
                key = k.find(" ") == -1 and k or k[:k.find(" ")]
                falls = k == (key+" = None")
                break
            
        if offset > 1:
            sb = b.get_sub_buffer(c)       
            sb.entries.pop()
            sb.size -= 1 
                   
            if falls:
                b.add("if "+key+" == "+"".join(sb.transpile()).rstrip()+" or "+key+" == None:")
            else:
                b.add("if "+key+ " == "+"".join(sb.transpile()).rstrip()+":")
        
        else:
            b.add("else:")
            
        b.new_line(1)
        
        ea = []
        end = offset+1
        while end < b.size:
            e = b.current(end)
            if (e.inset < c.inset or 
                (e.inset == c.inset and 
                (e.name == "case" or e.name == "default"))):
                break
            ea.append(e)
            end += 1
        
        sb = b.get_sub_buffer(None)     
        sb.entries = ea
        sb.size = len(ea)
        b.append_buffer(sb)
        b.trim()
        
        if e.inset < c.inset:
            b.new_line(-1)
            b.add("break")
            b.new_line(-1)
        
        elif not sb.size or b.peek().split()[0] != "break":
            b.new_line()
            b.add(key+" = None")
            b.new_line(-1)
        else:   
            b.new_line(-1)
            
        return offset+sb.size+1

    
class DefaultCaseFill(CodeRule):
    def __init__(self):
        super().__init__("default-case-fill", ["KW_default", "Separator"])
        
    def apply(self, b, offset):
        if not b.current().get_ancestor(KW_switch):
            return 0
        
        return CaseFill.apply(self, b, 1)
    
    
class LabelBreakFill(CodeRule):
    def __init__(self):
        super().__init__("label-break-fill", ["KW_break", "VariableType", "Separator"])
        
    def apply(self, b, offset):
        if b.current(2).name != ";":
            return 0
        
        b.add("break "+b.next().name)
        b.new_line()
        return 3
    

class PromiseCatchFill(CodeRule):
    def __init__(self):

        super().__init__("promise-catch-fill", ["FunctionEnd", "KW_catch", "Expression", "Begin"])
        
    def apply(self, b, offset):
        if b.current().extended is not b.next():
            return 0
        
        b.trim()
        b.add(").catch(")
        e = b.current(2)
        end = e.get_children().pop() 
        sb = b.get_sub_buffer(e, end)
        sb.offset += 1
        cnt = b.append_buffer(sb)
        b.trim()
        b.add(")")
        
        return cnt + 4


class SingletonFill(CodeRule):
    def __init__(self):
        super().__init__("singleton-function-fill", ["KW_function", "Declaration", "Constructor", "ANY", "End", "Block"])
        
    def apply(self, b, offset):
        if isinstance(b.current().par, RootEntry) or b.current(1).value:
            return 0
        
        c = b.current(2)        
        left = c.cf.spec[c.offs: b.current(offset-1).pos]
        right = c.cf.spec[b.current(offset).offs: c.pos]
                 
        fn = (left.startswith("(") and left or "("+left+")");
        nm = b.insert_function(fn+right)
        b.add(nm)
        
        # did not really need to us a lambda here!
        # if left == "()":
        #     b.add("lambda: " + nm + fn)
        # else:
        #     b.add("lambda "+ left + ": " + nm + fn)

        
        return b.get_sub_buffer(b.current(offset)).size + offset + 1
    
    
class MapHasFill(CodeRule):
    def __init__(self):
        super().__init__("Map-has-fill", ["Function","NameType","Begin","Expression","ANY","FunctionEnd"])
          
    def apply(self, b, offset):
        if b.next().name != "map" or not b.current().is_nested() or offset != 5:
            return 0
        
        v = b.current(4)
        if not isinstance(v, (VariableType, StringType, NumberType)):
            return 0
        
        if b.insert_prefix(str(v)+" in ", {"this": "self"}):
            return offset
        
        return 0
    
    
        
class DateNowFill(CodeRule):
    def __init__(self):
        super().__init__("Date-now-fill", ["GlobalType", "Function", "NameType", "Begin", "FunctionEnd"])
          
    def apply(self, b, offset):
        if b.current().name != "Date" or b.next().name != "now":
            return 0
        
        if not b.import_map.is_imported("time"):
            b.insert_import_statement("import {time} from 'time';")
        
        b.add("int(time() * 1000)")
        return offset+1

class JSONStringifyFill(CodeRule):
    def __init__(self):
        super().__init__("Date-now-fill", ["GlobalType", "Function", "NameType"])
          
    def apply(self, b, offset):
        if b.current().name != "JSON" or b.next().name != "stringify":
            return 0
        
        if not b.import_map.is_imported("json"):
            b.insert_import_statement("import {dumps} from 'json';")
        
        b.add("dumps")
        return offset+1

class UndefinedFill(CodeRule):
    
    factors = { }
    nested = True
    
    def __init__(self, name=None, path=None):
        super().__init__("undefined-fill", ["KW_undefined"])
        
    def apply(self, b, offset):
        b.add("None")
        return 1

class RefactorFunc(CodeRule):
    
    factors = { }
    nested = True
    
    def __init__(self, name=None, path=None):
        super().__init__(name or "refactor-functions", path or ["Function"])
        
    def apply(self, b, offset):
        if b.current().name in self.factors.keys():
            c = b.current()
            if c.is_nested() == self.nested:
                b.add(self.factors.get(c.name))
                return 2
            
        return 0
    
class RefactorFuncNoArgs(RefactorFunc):
        
    def __init__(self, name=None):
        super().__init__(name or "refactor-functions-no-args", ["Function", "NameType", "Begin", "FunctionEnd"])
    
    def apply(self, b, offset):
        if b.current().name in self.factors.keys():
            c = b.current()
            if c.is_nested() == self.nested:
                b.add(self.factors.get(c.name))
                b.add("()")
                b.add(b.current(3).extended and "." or " ")
                return 4
            
        return 0 
    
class RefactorBuiltins(RefactorFunc):
    
    factors = {
        "parseInt": "int",
        "parseFloat": "float",
        "Boolean": "bool",
        "Number": "float",
        "Uint8Array": "bytearray",
        "Set": "set"
        }
    
    nested = False 
    
    def __init__(self):
        super().__init__("refactor-built-in-functions")
        
class RefactorMisc(RefactorFunc):
    
    factors = {
        "push": "append"
        }
    
    def __init__(self):
        super().__init__("refactor-misc")
        
        
class RefactorNewInstance(CodeRule):
    factors = {
        "String": "str",
        "Uint8Array": "bytearray"
    }
    nested = False
    
    def __init__(self):
        super().__init__("refactor-new-instance", ["KW_new","Function","NameType"])
          
    def apply(self, b, offset):
        if b.next().name in self.factors.keys():
            b.add(self.factors.get(b.next().name))
            return 3
        
        return 0

        