'''jsconvert/jsrules/components.py

Provides a basic library of code rules for transpiling jsconvert DOM components
into javascript (ES6) source code.  These rules typically use heuristics to
determine the appropriate conversion methods and may apply to more than one
component at a time.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Nov 24, 2021

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
from jsconvert.comp import Extendable, Separator, VariableType, Expression
from jsconvert.lang import KW_do, KW_import

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = [
    "Comp", "NamType", "Attr", "Else", "Catch", 
    "CatchOnly", "Finaly", "DeclareVar", "ObjType", "ClosedStatementBlock", 
    "OpenStatementBlock", "DeclareLet", "DeclareConst", "DeclareClass", "DeclareClassExt", 
    "DoWhile", "ImportFrom", "Retrn", "ArrayBegin", "LabelStm", 
    "CaseStm", "BreakStm", "Meth", "Func", "Getr", "Setr", "Constr"]
    

class Comp(CodeRule):
    def __init__(self):
        super().__init__("Compare", ["Compare"])
        

    def apply(self, b, offset):
        b.add(b.current().name+" ")
        return 1
        

class Meth(CodeRule):
    def __init__(self, name="Method"):
        super().__init__(name, [name])
        

    def apply(self, b, offset):
        b.insert_code("")
        return 1
    
class Getr(Meth):
    def __init__(self):
        super().__init__("Getter")
        
class Func(Meth):
    def __init__(self):
        super().__init__("KW_function")
        
class Setr(Meth):
    def __init__(self):
        super().__init__("Setter")
        
class Constr(Meth):
    def __init__(self):
        super().__init__("KW_constructor")


class NamType(CodeRule):
    def __init__(self):
        super().__init__("NameType", ["Function", "NameType"])
        
    def apply(self, buffer, offset):
        buffer.add(str(buffer.current(1)))
        return 2
        

class NextStatement(CodeRule):
    def __init__(self, name, cls):
        super().__init__("end-"+name, ["End", cls])
        
    def apply(self, b, offset):
        if b.current().name != "}":
            return 0
            
        b.trim()
        b.new_line(-1)
        b.add("} ")
        b.add(self.name[4:])
        if not isinstance(b.current(offset+1), Expression):
            b.space()
            
        return 2
        
    
class Else(NextStatement):
    def __init__(self):
        super().__init__("else", "KW_else")
    
    
class Catch(NextStatement):
    def __init__(self):
        super().__init__("catch", "KW_catch")
        
        
class CatchOnly(NextStatement):
    def __init__(self):
        super().__init__("catch", "XW_catch")


class Finaly(NextStatement):
    def __init__(self):
        super().__init__("finally", "KW_finally")

    
# class ObjStatementType(CodeRule):
#     def __init__(self):
#         super().__init__("single_statement", ["ObjectType", "Block"])
#
#     def apply(self, b, offset):
#         if b.current(2).name == "{":
#             return 0
#
#         b.new_line(1)
#         return 2 

class ClosedStatementBlock(CodeRule):
    def __init__(self):
        super().__init__("open_statment_block", ["StatementBlock", "Block", "Begin"])

    def apply(self, b, offset):
        b.add("{")
        b.new_line(1)
        return 3 

class OpenStatementBlock(CodeRule):
    def __init__(self):
        super().__init__("closed_statment_block", ["StatementBlock", "Block"])

    def apply(self, b, offset):
        sb = b.get_sub_buffer(b.next())
        b.new_line(1)

        while sb.offset < sb.size:
            sb.rules.process(sb)
        
        b.add(("".join(sb.buf)).strip())
        ofs = sb.size + 2
        
        if b.current(ofs).name == ";":
            b.add(";")
            ofs += 1

        b.new_line(-1)
        return ofs      


    
class ObjType(CodeRule):
    def __init__(self):
        super().__init__("object-type", ["ObjectType"])
        
    def apply(self, b, offset):
        c = b.current()
        sb = b.get_sub_buffer(c)
        sb.inobject = True
        
        ch = c.get_children()
        sb.add("{")
        sb.new_line(1)
        cnt = 2
        ln = len(ch)
        i = 1
        
        while i < ln:
            c = ch[i]
            if c.name == ":":
                i += 1
                sb.add(": ")
                cnt += sb.append_buffer(sb.get_sub_buffer(ch[i]))+1
            elif c.name == ",":
                sb.trim()
                sb.add(",")
                sb.new_line()
            elif c.name == "}":
                sb.trim()    
                sb.new_line(-1)
                sb.add("}")
                if c.extended:
                    sb.add(".")
            elif isinstance(c, VariableType):
                sb.add(c.name)
            else:
                sb.add(str(c))
            
            cnt += 1
            i += 1
        
        sb.offset = sb.size    
        b.append_buffer(sb)            
        return cnt      

class Declareable(CodeRule):
    def __init__(self, name, entry):
        super().__init__(name, [entry])
     
    def apply(self, b, offset):
        b.add(str(b.current()))
        if not isinstance(b.next(), Separator):
            b.space()
            
        return 1
    
    
class DeclareVar(Declareable):
    def __init__(self):
        super().__init__("declare_var", "KW_var")
     
    
class DeclareLet(Declareable):
    def __init__(self):
        super().__init__("declare_let", "KW_let")
     
    
class DeclareConst(Declareable):
    def __init__(self):
        super().__init__("declare_const", "KW_const")

     
class Attr(Declareable):
    def __init__(self):
        super().__init__("Attribute", "Attribute")

    
class DoWhile(CodeRule):
    def __init__(self):
        super().__init__("do_while", ["End", "KW_while"])
     
    def apply(self, b, offset):
        if not isinstance(b.current(1).get_previous(), KW_do):
            return 0
        
        b.trim()
        b.new_line(-1)
        b.add("} while")
        return 2 


class ImportFrom(CodeRule):
    def __init__(self):
        super().__init__("import_from", ["KW_from"])
     
    def apply(self, b, offset):
        if not isinstance(b.current().par, KW_import):
            return 0
        
        b.trim()
        b.add(" from ")
        return 1 


class Retrn(Declareable):
    def __init__(self):
        super().__init__("return", "KW_return")  


class ArrayBegin(CodeRule):
    def __init__(self):
        super().__init__("array_begin", ["ArrayType", "Begin"])
        
    def apply(self, b, offset):
        if isinstance(b.prev(), Extendable):
            b.trim()
            
        b.add("[")
        return 2

 
class LabelStm(CodeRule):
    def __init__(self):
        super().__init__("Label", ["Label", "Separator"])
        
    def apply(self, b, offset):
        b.add(b.current().value+":")
        b.new_line()
        return 2


class CaseStm(CodeRule):
    def __init__(self):
        super().__init__("case", ["KW_case", "ANY", "End"])
        
    def apply(self, b, offset):
        sb = b.get_sub_buffer(b.current())
        
        while sb.offset < sb.size:
            sb.rules.process(sb)
        
        b.trim()
        b.new_line()       
        b.add("case "+("".join(sb.buf)).strip())
        b.space()

        return sb.size+1

class DeclareClass(CodeRule):
    def __init__(self):
        super().__init__("class-extension", ["KW_class", "Declaration"])
        
    def apply(self, b, offset):
        b.insert_code("")
        b.add(str(b.next()))
        b.space()

        return 2
    
class DeclareClassExt(CodeRule):
    def __init__(self):
        super().__init__("declare-class-extension", ["KW_class", "Declaration", "KW_extends"])
        
    def apply(self, b, offset):
        b.insert_code("")
        b.add(str(b.next()) + " "+str(b.current(offset)))
        b.space()

        return 3
    
class BreakStm(CodeRule):
    def __init__(self):
        super().__init__("Break", ["KW_break"])
        
    def apply(self, b, offset):
        b.add(b.current().name)
        if not b.next().name == ";":
            b.space()
            
        return 1
