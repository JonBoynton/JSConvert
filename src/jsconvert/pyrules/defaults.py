'''jsconvert/pyrules/defaults.py

Provides a library of default code rules for transpiling of jsconvert DOM
components into Python source code. Default rules tend to be very simple and are
often overriden by rules with more sophisticated heuristics. For this reason,
they should be the last rules loaded into the Rules Manager.

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

from jsconvert.transpiler import CodeRule, DefaultRule

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = [
    "VarTyp", "FuncEnd", "ObjEnd", "ArryEnd", "StringTyp", 
    "NumberTyp", "GlobalTyp", "BoolTyp", "NullTyp", "Rule1", 
    "Rule2"
    ]


class VarTyp(CodeRule):
    def __init__(self):
        super().__init__("variable", ["VariableType"])
        
    def apply(self, b, offset):
        c = b.current()
        b.add(c.get_local_name())
        b.add(c.extended and "." or " ")            
        return 1
        

class Extender(CodeRule):
    """Abstract rule that appends component string value followed by a '.' or ' ' dot as needed."""
    
    def __init__(self, name, trim=False):
        super().__init__(name, [name])
        self.trim = trim
        
    def apply(self, b, offset):
        c = b.current()
        if self.trim:
            b.trim()
        b.add(str(c))
        b.add(c.extended and "." or " ")
            
        return 1             
            
            
class FuncEnd(Extender):
    def __init__(self):
        super().__init__("FunctionEnd", True) 
    

class ObjEnd(Extender):
    def __init__(self):
        super().__init__("ObjectEnd", True) 

    
class ArryEnd(Extender):
    def __init__(self):
        super().__init__("ArrayEnd", True) 

                
class NumberTyp(Extender):
    def __init__(self):
        super().__init__("NumberType")
        
        
class GlobalTyp(Extender):
    def __init__(self):
        super().__init__("GlobalType")
        
        
class BoolTyp(Extender):
    def __init__(self):
        super().__init__("BooleanType")

        
class StringTyp(Extender):
    def __init__(self):
        super().__init__("StringType")
        
        
class NullTyp(CodeRule):
    def __init__(self):
        super().__init__("null-type", ["KW_null"])
        
    def apply(self, b, offset):
        b.add("None")
        return 1

        
class Rule1(DefaultRule):
    def __init__(self):
        super().__init__("defult_rule1", [
            "Separator", "Begin", "End", "NameType", "KW_break", "KW_while", "KW_switch",
            "KW_for","KW_try", "KW_continue", "Operator",
            "KW_null", "KW_constructor", "KW_undefined"])

        
class Rule2(DefaultRule):
    def __init__(self):
        super().__init__("defult_rule2", [
            "Modifier", "Keyword", "KW_do", "KW_if", "KW_catch", "KW_case", "KW_break",
            "KW_return", "KW_extends", "KW_finally", "TernaryStatement"], " ")
        