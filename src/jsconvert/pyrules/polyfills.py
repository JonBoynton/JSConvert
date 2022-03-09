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
from jsconvert.comp import Assignment, Extendable, RootEntry, Expression
from jsconvert.lang import KW_switch

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["TrueFill", "FalseFill", "TypeFill", "InstanceFill", "ToStringFill", 
    "CharCodeFill", "CharAtFill", "LengthFill", "SwitchFill", "CaseFill", "DefaultCaseFill",
    "LabelBreakFill", "PromiseCatchFill", "SingletonFill", "SubstringFill", "IndexOfFill",
    "RefactorFunc", "RefactorBuiltins", "FromCharCodeFill"
    ]


# searches the buffer in reverse to find a string matching the "e" entry name then inserts a token
def _insert_prefix(e, buffer, token):
    while isinstance(e.par, Extendable) and e.par.extended is e:
        e = e.par
        
    nm = e.name or str(e)
    if nm == "this":
        nm = "self"
        
    for i in range(len(buffer.buf)-1, -1, -1):
    # for i in reversed(range(0, len(buffer.buf))):
        if buffer.buf[i] == nm:
            buffer.buf.insert(i, token)
            break


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
    def __init__(self):
        super().__init__("instance-fill", ["VariableType", "KW_instanceof", "VariableType"])
        
    def apply(self, b, offset):
        b.add("isinstance("+b.current().name+", "+b.current(2).name+")")
        return 3
    

class ToStringFill(CodeRule):
    def __init__(self):
        super().__init__("toString-fill", ["Function", "NameType", "Begin", "FunctionEnd"])
           
    def apply(self, b, offset):
        if b.next().name != "toString" or not b.current().is_nested():
            return 0
        
        b.buf.pop()
        _insert_prefix(b.current(), b, "str(")
        b.add(")")
        b.add(b.current(offset).extended and "." or " ")
        return 4

    
class CharCodeFill(CodeRule):
    def __init__(self):
        super().__init__("charCodeAt-fill", ["Function", "ANY", "FunctionEnd"])
          
    def apply(self, b, offset):
        if b.next().name != "charCodeAt" or not b.current().is_nested():
            return 0
        
        b.buf.pop()
        _insert_prefix(b.current(), b, "ord(")
        
        sb = b.get_sub_buffer(b.current())
        sb.entries = sb.entries[2:sb.size-1]
        sb.size -= 3
        b.add("["+"".join(sb.transpile()).rstrip()+"]")
        return  offset

    
class FromCharCodeFill(CodeRule):
    def __init__(self):
        super().__init__("from-charcode-fill", ["GlobalType", "Function", "NameType"])
          
    def apply(self, b, offset):
        if b.current().name == "String" and b.next().name == "fromCharCode":
            b.add("chr")
            return 3
        
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
              
    
class LengthFill(CodeRule):
    def __init__(self):
        super().__init__("length-fill", ["VariableType"])
                
    def apply(self, b, offset):
        if (b.current().name != "length" or
            not b.current().is_nested() or
            isinstance(b.next(), Assignment)):
            return 0
        
        b.buf.pop()
        _insert_prefix(b.prev(), b, "len(")
        b.add(")")            
        b.add(b.current().extended and "." or " ")            
        return 1
    
   
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
    
        if left == "()":
            b.add("lambda: " + nm + fn)
        else:
            b.add("lambda "+ left + ": " + nm + fn)

        
        return b.get_sub_buffer(b.current(offset)).size + offset + 1


class SubstringFill(CodeRule):
    def __init__(self):
        super().__init__("substring-fill", ["Function", "ANY", "FunctionEnd"])
        
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
   
        
class IndexOfFill(CodeRule):
    def __init__(self):

        super().__init__("indexOf-fill", ["Function", "NameType", "Begin", "Expression", "StringType"])
        
    def apply(self, b, offset):
        if b.current().name == "indexOf" and b.current().is_nested():
            b.add("find")
            return 2 
        
        return 0   


class RefactorFunc(CodeRule):
    
    factors = {
        "startsWith": "startswith",
        "endsWith": "endswith",
        "trim": "strip"
        }
    
    nested = True
    
    def __init__(self, name=None):
        super().__init__(name or "refactor-functions", ["Function"])
        
    def apply(self, b, offset):
        if b.current().name in self.factors.keys():
            c = b.current()
            if c.is_nested() == self.nested:
                b.add(self.factors.get(c.name))
                return 2
            
        return 0

 
class RefactorBuiltins(RefactorFunc):
    
    factors = {
        "parseInt": "int",
        "parseFloat": "float",
        "Boolean": "bool"
        }
    
    nested = False 
    
    def __init__(self):
        super().__init__("refactor-built-in-functions")
        