'''jsconvert/pyrules/separators.py

Provides a set of code rules containing special heuristics for transpiling and
formatting of various separator characters for use (or omission) in Python
source code.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Nov 21, 2021

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
from jsconvert.comp import ForCondition, Condition, Expression, Constructor

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = [
    "OpenBrace", "CloseBrace", "Semicolon", "Commas", "OpenParenthesis", 
    "CloseParenthesis", "CloseExpression", "UndefVarDecl", "UndefLetDecl"
    ]

    
def _is_in_condition(e):
    return isinstance(e.par, Expression) and e.get_ancestor(Condition) is e.par.par


class OpenBrace(CodeRule):
    def __init__(self):
        super().__init__("opening_brace", ["Begin"])
        
    def apply(self, b, offset):
        if b.current().name != "{":
            return 0
        
        b.trim()
        b.add(":")
        b.new_line(1)
        if isinstance(b.current().par.par, Constructor):
            b.heading.mark()
        return 1


class CloseBrace(CodeRule):
    def __init__(self):
        super().__init__("closing_brace", ["End"])
        
    def apply(self, b, offset):
        if b.current().name != "}":
            return 0
        
        b.trim()
        b.new_line(-1) 
        if b.next().name == ";":
            b.new_line() 
            return 2
            
        b.new_line()
        return 1 


class Semicolon(CodeRule):
    def __init__(self):
        super().__init__("semicolon", ["Separator"])
    
    def apply(self, b, offset):
        c = b.current()
        if c.name != ";":
            return 0
        
        b.trim()
        if isinstance(c.par, ForCondition):
            b.add("; ")

        else:
            b.new_line()
            
        return 1


class Commas(CodeRule):
    def __init__(self):
        super().__init__("commas", ["Separator"])
    
    def apply(self, b, offset):
        if b.current().name != ",":
            return 0
        
        b.trim()
        b.add(", ")
            
        return 1
   
            
class OpenParenthesis(CodeRule):
    def __init__(self):
        super().__init__("open_parenthesis", ["Begin"])

    def apply(self, b, offset):
        if b.current().name != "(":
            return 0
        
        c = b.current()
        if _is_in_condition(c) and not c.get_previous():
            if not b.peek().isspace():
                b.space()
            return 1
  
        b.add("(")
        return 1 
    
class CloseParenthesis(CodeRule):
    def __init__(self):
        super().__init__("close_parenthesis", ["End"])

    def apply(self, b, offset):
        if b.current().name != ")":
            return 0
        
        c = b.current()
        if _is_in_condition(c) and not c.get_next():
            return 1
        
        b.trim()
        b.add(")")
        return 1 
    
class CloseExpression(CodeRule):
    def __init__(self):
        super().__init__("ExpressionEnd", ["ExpressionEnd"])
        
    def apply(self, b, offset):
        c = b.current()
        if isinstance(c.par.par, Condition):
            return 1
        
        if c.par.is_enclosed:
            b.trim()
            b.add(")")
            b.add(b.current().extended and "." or " ")
            
        return 1
     
class UndefinedDecl(CodeRule):
    def __init__(self, name):
        super().__init__("undefined-"+name+"-declaration", ["KW_"+name, "Separator"])
        
    def apply(self, b, offset):
        if b.next().name == ";":
            b.add(b.current().value)
            b.add(" = None")
            b.new_line()
            return 2
            
        return 1
    
class UndefVarDecl(UndefinedDecl):
    def __init__(self):
        super().__init__("var")
        
class UndefLetDecl(UndefinedDecl):
    def __init__(self):
        super().__init__("let")
        
        
