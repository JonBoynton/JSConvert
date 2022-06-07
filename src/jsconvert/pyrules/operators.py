'''jsconvert/pyrules/operators.py

Provides a set of code rules containing special heuristics for transpiling of
various javascript operators into Python source code.

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
from jsconvert.comp import Extendable, Assignment
# from jsconvert.comp import VariableType, StringType

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["NotOp", "TildaOp", "OrBool", "AndBool", "EqOp", 
    "IsEqOp", "NotEqOp", "IsNotEqOp", "LeftIncrOp", "AssignLeftIncrOp", 
    "RightIncrOp", "ThisRightIncrOp", "AssignRightIncrOp", "ThisAssignRightIncrOp", "ShiftUnSign", 
    "PrecedenceOper", "Comp", "Oper"
    ]


def _parse_var_name(e):
    nm = e.get_full_name()
    if nm.startswith("this") and (len(nm) == 4 or nm[4] == "."):
        return "self"+nm[4:]
    
    return nm


class NotOp(CodeRule):
    def __init__(self):
        super().__init__("not-operator", ["Operator"])
        
    def apply(self, b, offset):
        if b.current().name != "!":
            return 0
        
        b.add("not ")
        return 1
    
    
class OrBool(CodeRule):
    def __init__(self):
        super().__init__("or-boolean", ["Operator"])
        
    def apply(self, b, offset):
        if b.current().name != "||":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add("or")
        b.space() 
            
        return 1


class AndBool(CodeRule):
    def __init__(self):
        super().__init__("and-boolean", ["Operator"])
        
    def apply(self, b, offset):
        if b.current().name != "&&":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add("and")
        b.space()            
        return 1

    
class TildaOp(CodeRule):
    def __init__(self):
        super().__init__("tilda-operator", ["Operator"])
        
    def apply(self, b, offset):
        if b.current().name != "~":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add("~")            
        return 1


class EqOp(CodeRule):
    def __init__(self):
        super().__init__("equal-to", ["Compare"])
               
    def apply(self, b, offset):
        if b.current().name != "===":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add("==")
        b.space()           
        return 1
    
    
class IsEqOp(CodeRule):
    def __init__(self, name=None, path=None):
        super().__init__(name or "equal-to", path or ["VariableType", "Compare", "VariableType"])
               
    def apply(self, b, offset):
        if b.next().name != "===":
            return 0
        
        b.add(str(b.current()))
        b.add(" is ")
        b.add(str(b.current(2)))           
        return 3


    
# don't think this happens    
# class IsStringEqOp(IsEqOp):
#     def __init__(self):
#         super().__init__("equal-to", ["StringType", "Compare", "StringType"])
#

    
class NotEqOp(CodeRule):
    def __init__(self):
        super().__init__("not-equal-to", ["Compare"])
                
    def apply(self, b, offset):
        if b.current().name != "!==":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add("!=")
        b.space()           
        return 1
    
    
class IsNotEqOp(CodeRule):
    def __init__(self, name=None, path=None):
        super().__init__(name or "equal-to", path or ["VariableType", "Compare", "VariableType"])
               
    def apply(self, b, offset):
        if b.next().name != "!==":
            return 0
        
        b.add(str(b.current()))
        b.add(" is not ")
        b.add(str(b.current(2)))           
        return 3
    

# don't think this happens    
# class IsNotStringEqOp(IsNotEqOp):
#     def __init__(self):
#         super().__init__("equal-to", ["StringType", "Compare", "StringType"])
#
#

        
class Comp(CodeRule):
    def __init__(self):
        super().__init__("Compare", ["Compare"])       

    def apply(self, b, offset):
        if not b.peek().isspace():
            b.space()
        b.add(b.current().name)
        b.space()           
        return 1
    
    
class ShiftUnSign(CodeRule):
    def __init__(self):
        super().__init__("shift-unsigned", ["Operator"])       

    def apply(self, b, offset):
        if b.current().name != ">>>":
            return 0
        
        if not b.peek().isspace():
            b.space()
        b.add(">>")
        b.space()           
        return 1
    
    
class PrecedenceOper(CodeRule):
    def __init__(self):
        super().__init__("precedence-operator", ["Operator"])    

    def apply(self, b, offset):
        c = b.current()
        if c.name == "*" or c.name == "/":
            b.trim()
            b.add(c.name)
            return 1

        return 0
    
            
class Oper(CodeRule):
    def __init__(self):
        super().__init__("any-operator", ["Operator"])
        
    def apply(self, b, offset):
        c = b.current()
        if c.name == "++" or c.name == "--":
            return 0
        
        b.space()        
        b.add(c.name)
        
        # only add a space if in an expression
        if isinstance(b.prev(), (Extendable, Assignment)):
            b.space()
            
        return 1
    
    
class LeftIncrOp(CodeRule):
    def __init__(self):
        super().__init__("left-incr-operator", ["Increment", "Operator"])
       
    def apply(self, b, offset):
        c = b.current(offset+1)
        offset += c.get_extent()+1
        
        if b.current(offset).name == ";":
            b.add(_parse_var_name(c) + " " + b.current(1).name[0:1] + "= 1")
            return offset
        
        b.add(b.current().name)                   
        return 2
    
       
class AssignLeftIncrOp(CodeRule):
    def __init__(self):
        super().__init__("assign-left-incr-operator", [
            "Assignment", "Operator", "Expression", "Increment", "Operator"])
        
    def apply(self, b, offset):
        c = b.current(offset+1)
        offset += c.get_extent()+1
        
        if b.current(offset).name != ";" or not b.insert_code(
            _parse_var_name(c) + " " + b.current(3).name[0:1] + "= 1"):
            return 0
        
        b.space()
        b.add(b.next().name + " " + _parse_var_name(c))
        return offset

    
class RightIncrOp(CodeRule):
    def __init__(self):
        super().__init__("right-incr-operator", ["Increment", "VariableType"])

    def apply(self, b, offset):
        c = b.current(offset)
        offset += c.get_extent()+1
        
        if b.current(offset).name == ";":
            b.add(_parse_var_name(c) + " " + b.current().name[0:1] + "= 1")
        else:
            b.add(_parse_var_name(b.next())+b.current().name+" ")
        return offset 
    
           
class ThisRightIncrOp(CodeRule):
    def __init__(self):
        super().__init__("this-right-incr-operator", ["Increment", "KW_this"])

    def apply(self, b, offset):
        return RightIncrOp.apply(self, b, offset)
        
                
class AssignRightIncrOp(CodeRule):
    def __init__(self):
        super().__init__("assign-right-incr-operator", [
            "Assignment", "Operator", "Expression", "Increment", "VariableType"])
        
    def apply(self, b, offset):
        c = b.current(offset)
        offset += c.get_extent()+1
        
        if b.current(offset).name != ";":
            return 0
        
        b.space()
        b.add(b.next().name + " " + _parse_var_name(c))
        b.new_line()
        b.add(_parse_var_name(c) + " " + b.current(3).name[0:1] + "= 1")
        return offset

    
class ThisAssignRightIncrOp(CodeRule):
    def __init__(self):
        super().__init__("this-assign-right-incr-operator", [
            "Assignment", "Operator", "Expression", "Increment", "KW_this"])
        
    def apply(self, b, offset):
        return AssignRightIncrOp.apply(self, b, offset)
    