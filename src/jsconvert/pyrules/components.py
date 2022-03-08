'''jsconvert/pyrules/components.py

Provides a basic library of code rules for transpiling jsconvert DOM components
into Python source code.  These rules typically use heuristics to determine the
appropriate conversion methods and may apply to more than one component at a
time.

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
from jsconvert.comp import (
    Extendable,
    Expression,
    Attribute,
    VariableType,
    NameType,
    StringType, 
    End, 
    Method, 
    Assignment, 
    RootEntry,
    Constructor,
    Declaration,
    Block,
    StatementBlock,
    TernaryExpression
    )
from jsconvert.lang import KW_do, KW_import, KW_if, KW_class

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["ObjType", "GlobalVar", "Attr", "FunctionDecl",
    "Else", "EndElse", "ClosedStatementBlock", "OpenStatementBlock", "DeclareVar", 
    "DeclareLet", "DeclareConst", "DoWhile", "ImportFrom", "ThisType", 
    "SuperType", "ArrayBegin", "LabelStm", "ImportStm", "ImportFromStm", 
    "LambdaFunc", "TernaryExpr", "DeclareGet", "DeclareSet", "DeclareMethod", 
    "EmptyMethodDecl", "ConstructorDecl", "ClassDecl", "CatchOnly", "WhileStm"
    ]


def _clean_import_package(name):
    if name.endswith(".js"):
        name = name[: len(name)-3]
    elif name.endswith(".jsx"):
        name = name[: len(name)-3]
    
    if name.startswith("."):    
        if name.startswith("./"):
            name = "."+name[2:]
        elif name.startswith("../"):
            name = ".."+name[3:]
            
    return name


def _is_global_scope(e):
    return isinstance(e, RootEntry) or (isinstance(e, Block) and  
        isinstance(e.par, StatementBlock) and
        isinstance(e.par.par, KW_class))


        
class LambdaFunc(CodeRule):
    def __init__(self):
        super().__init__("lambda_function", ["Lambda", "ANY", "Operator"])
        
    def apply(self, b, offset):
        c = b.current()
        sb = b.get_sub_buffer(b.current(offset+1))
        
        if isinstance(b.current(offset+1), Expression):
            if offset == 3:
                b.add("lambda: ")
                b.append_buffer(sb)
            else:
                b.add("lambda ")
                b.append_buffer(b.get_slice(b.offset+1, b.offset+offset))
                b.add(": ")
                b.append_buffer(sb)

        else:
            sa = c.cf.spec[c.offs: c.pos].split("=>", 1)
            left = sa[0].rstrip()
            right = sa[1].lstrip() 
                     
            fn = (left.startswith("(") and left or "("+left+")");
            nm = b.insert_function(fn+right)
        
            if left == "()":
                b.add("lambda: " + nm + fn)
            else:
                b.add("lambda "+ left + ": " + nm + fn)

                
        return offset + sb.size + 2


class TernaryExpr(CodeRule):
    def __init__(self):
        super().__init__("ternary_expression", ["TernaryExpression"])
        
        
    def apply(self, b, offset):
        c = b.current() 
        enclose = isinstance(c.par, TernaryExpression) and not c.par.is_enclosed
        
        if enclose:
            b.add("(")
                   
        ch = c.get_children()
        ofs = 0
        if ch[0].name == "(":
            b.add("(")
            ofs = 1
            
        cnt = b.append_entry(ch[2+ofs])
        b.trim()
        b.add(" if ")
        sb = b.get_sub_buffer(ch[ofs])
        cnt += b.append_buffer(sb)
        b.trim()
        b.add(" else ")
        cnt += b.append_entry(ch[4+ofs])
        
        if enclose:
            b.trim()
            b.add(")")
        
        return cnt + 4 + ofs
         
    
class ImportStm(CodeRule):
    def __init__(self):
        super().__init__("import_stm", ["KW_import"])
        
    def apply(self, b, offset):
        sb = b.get_sub_buffer(b.current()) 
        s = ""
        for e in sb.entries:
            if (e.name == "{" or 
                e.name == "}" or
                e.name == "import"):
                continue
            
            if isinstance(e, Attribute):
                s += e.value
            elif isinstance(e, NameType):
                s += e.name
            elif isinstance(e, StringType):
                s += e.value_of()
            elif e.name == ",":
                s += ", "
            elif e.name == "as":
                s += " as "
                
        b.add("import ")
        b.add(_clean_import_package(s))
        b.mark_header_offset()
        return sb.size+1
               
           
class ImportFromStm(CodeRule):
    def __init__(self):
        super().__init__("import_from_stm", ["KW_import", "ANY", "KW_from"])
        
    def apply(self, b, offset):
        sb = b.get_sub_buffer(b.current()) 
        
        s = ""
        for e in sb.entries:
            if (e.name == "{" or 
                e.name == "}" or
                e.name == "import"):
                continue
            
            if isinstance(e, Attribute):
                s += e.value
            elif isinstance(e, NameType):
                s += e.name
            elif e.name == ",":
                s += ", "
            elif e.name == "as":
                s += " as "
            elif e.name == "from":
                break
            
        b.add("from ")
        end = sb.entries.pop()
        fs = isinstance(end, StringType) and end.value_of() or str(end)        
        b.add(_clean_import_package(fs))
        b.add(" import ")
        b.add(s)
        b.mark_header_offset()
        return sb.size+1
    

class ImportFrom(CodeRule):
    def __init__(self):
        super().__init__("import_from", ["KW_from"])
     
    def apply(self, b, offset):
        if not isinstance(b.current().par, KW_import):
            return 0
        
        b.trim()
        b.add(" from ")
        return 1 
        return 1        

    
class ObjType(CodeRule):
    def __init__(self):
        super().__init__("object_type", ["ObjectType"])
        
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
                sb.add('"'+c.name+'"')
            else:
                sb.add(str(c))
            
            cnt += 1
            i += 1
        
        sb.offset = sb.size    
        b.append_buffer(sb)            
        return cnt      
   
# start here!!! I would like to use NameType to identify built-in Classes instead of VariableType
# we need to create some code in Container that checks for varible declarations for var,let,conts, and Attribute
# This may effect this code, also we could add 'Assignment' and 'Increment' variation for  GlobalVar below

# adds a global variable to a top level function or class method when locally assigned
class GlobalVar(CodeRule):
    def __init__(self):
        super().__init__("global_varible", ["VariableType"])
    
    def apply(self, b, offset):
        if b.peek() != "." and isinstance(b.next(), Assignment):
            c = b.current()
            con = c.get_container()
            while not isinstance(con, RootEntry):
                if b.import_map.is_imported(c.name) or con.is_declared(c.name, local=True):
                    break
                
                if isinstance(con, Constructor)  and _is_global_scope(con.par):
                    b.heading.insert(con.scope+c.name, "global "+c.name)
                    break
                    
                con = con.get_container()
            
        return 0
               
        
class ThisType(CodeRule):
    def __init__(self):
        super().__init__("this", ["KW_this"])
        
    def apply(self, b, offset):
        b.add("self")
        if b.current().extended:
            b.add(".")  
        return 1 

          
class SuperType(CodeRule):
    def __init__(self):
        super().__init__("this", ["KW_super"])

        
    def apply(self, b, offset):
        b.add("super")
        if b.current().extended:
            b.add(".")    
        return 1 
                  

class Else(CodeRule):
    def __init__(self):
        super().__init__("else", ["KW_else"])
        
    def apply(self, b, offset):
        b.trim()
        b.new_line(-1)
        if isinstance(b.next(), KW_if):
            b.add("elif")
            return 2
        
        b.add("else")
        return 1
    
class EndElse(CodeRule):
    def __init__(self):
        super().__init__("end_else", ["End", "KW_else"])
        
    def apply(self, b, offset):
        if b.current().name != "}":
            return 0
            
        b.trim()
        b.new_line(-1)
        if isinstance(b.current(2), KW_if):
            b.add("elif")
            return 3
        
        b.add("else")
        return 2
    
class ClosedStatementBlock(CodeRule):
    def __init__(self):
        super().__init__("open_statment_block", ["StatementBlock", "Block", "Begin"])

    def apply(self, b, offset):
        b.trim()
        b.add(":")
        b.new_line(1)
        if isinstance(b.current(offset+1), End):
            b.add("pass")
        return 3 

class OpenStatementBlock(CodeRule):
    def __init__(self):
        super().__init__("closed_statment_block", ["StatementBlock", "Block"])

    def apply(self, b, offset):
        sb = b.get_sub_buffer(b.next())
        b.trim()
        b.add(":")
        b.new_line(1)
        
        if not b.append_buffer(sb):
            b.add("pass")
            
        b.trim()
        ofs = sb.size + 2
        
        if b.current(ofs).name == ";":
            ofs += 1

        b.new_line(-1)
        return ofs          

class Declareable(CodeRule):
    def __init__(self, name, entry):
        super().__init__(name, [entry])
     
    def apply(self, b, offset):
        c = b.current()
        if c.value == "def":
            c.value = "x_def"
        b.add(c.get_prop(c.value))
        if not isinstance(c, Method):
            b.add(" ")
            
        if b.next().name == ";":
            b.add("= None")
                        
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

        
class WhileStm(CodeRule):
    def __init__(self):
        super().__init__("while_statement", ["KW_while", "Expression", "ANY", "ExpressionEnd"])
     
    def apply(self, b, offset):
        b.add("while")
        b.add(" ")
        sb = b.get_sub_buffer(b.next(), b.current(offset))
        b.append_buffer(sb)
        return offset+1
    
     
class DoWhile(CodeRule):
    def __init__(self):
        super().__init__("do_while", ["End", "KW_while"])
     
    def apply(self, b, offset):
        if not isinstance(b.current(1).get_previous(), KW_do):
            return 0
        
        b.trim()
        b.new_line(-1)
        b.add("}")
        return 1 
    

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
    

class FunctionDecl(CodeRule):
    def __init__(self):
        super().__init__("function", ["KW_function", "Declaration"])
        
    def apply(self, b, offset):
        b.add("def "+b.next().value)                   
        return 1
    
    
class ConstructorDecl(CodeRule):
    def __init__(self):
        super().__init__("constructor_declaration", ["KW_constructor", "Declaration", "Constructor", "Begin"])
        
    def apply(self, b, offset):
        b.new_line()
        b.add("def __init__(self")
        if b.current(4).name != ")":
            b.add(", ")                   
        return 4
    
    
class MethodDecl(CodeRule):
    def __init__(self, name, entry):
        super().__init__(name, [entry, "Declaration", "Constructor", "Begin"])
        
    def apply(self, b, offset):
        b.new_line()
        b.add("def "+b.next().value+"(self")
        if b.current(4).name != ")":
            b.add(", ")                   
        return 4

    
class DeclareMethod(MethodDecl):
    def __init__(self):
        super().__init__("method_declaration", "Method")
        
    
class DeclareGet(MethodDecl):
    def __init__(self):
        super().__init__("declare_get", "Getter")

    def apply(self, b, offset):
        b.new_line()
        b.add("@property")
        return super().apply(b, offset)

        
class DeclareSet(MethodDecl):
    def __init__(self):
        super().__init__("declare_set", "Setter")
        
    def apply(self, b, offset):
        b.new_line()
        b.add("@"+b.next().value+".setter")
        return super().apply(b, offset)
    
        
class EmptyMethodDecl(CodeRule):
    def __init__(self):
        super().__init__("empty_method_declaration", ["Method", "Declaration", "Constructor", "Begin", "End", "Block", "Begin", "End"])
        
    def apply(self, b, offset):
        b.new_line()
        b.add("def "+b.next().value+"(self):")
        b.new_line(1)
        b.add("pass")
        b.new_line(-1)            
        return offset+1
    
        
class ClassDecl(CodeRule):
    def __init__(self):
        super().__init__("class_declaration", ["KW_class", "Declaration"])
        
    def apply(self, b, offset):
        b.new_line()
        b.add("class "+b.next().value+"(")
        if isinstance(b.current(2), Declaration):
            b.add(b.next().value+")")
            return 3
        b.add(")")                  
        return 2
    
    
class CatchOnly(CodeRule):
    def __init__(self):

        super().__init__("promise_catch_fill", ["XW_catch"])

    def apply(self, b, offset):

        b.add("catch")
        return 2     
    
