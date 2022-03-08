'''jsconvert/jsrules/operators.py

Provides a set of code rules containing special heuristics for transpiling of
various javascript operators into javascript (ES6) source code.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Nov 23, 2021

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
from jsconvert.comp import Begin

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["NotOp", "OrOp", "TildaOp", "Oper", "RightIncrOp", "LeftIncrOp"]


class NotOp(CodeRule):
    def __init__(self):
        super().__init__("not-operator", ["Operator"])
        
        
    def apply(self, b, offset):
        if b.current().name != "!":
            return 0
        
        if isinstance(b.current().get_previous(), Begin):
            b.trim()
            
        b.add("!")
        return 1


class OrOp(CodeRule):
    def __init__(self):
        super().__init__("or-operator", ["Operator"])


    def apply(self, b, offset):
        if b.current().name != "|":
            return 0

        b.trim()
        b.add("|")        


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
        
            
class Oper(CodeRule):
    def __init__(self):
        super().__init__("any-operator", ["Operator"])
        

    def apply(self, b, offset):        
        b.add(b.current().name+" ")
        return 1
    

class LeftIncrOp(CodeRule):
    def __init__(self):
        super().__init__("left-incr-operator", ["Increment", "Operator", "VariableType"])
        
        
    def apply(self, b, offset):
        b.add(b.current().name)                   
        return 2

    
class RightIncrOp(CodeRule):
    def __init__(self):
        super().__init__("right-incr-operator", ["Increment", "ANY", "Operator"])

    def apply(self, b, offset):
        if offset == 1:
            return 0
        
        b.add(b.next().get_full_name() + b.current().name) 
        return offset+1         
        