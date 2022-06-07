'''jsconvert/pyrules/errors.py

Provides a library of code rules for transpiling of error and exception related
jsconvert DOM components into Python source code.

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

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

__all__ = ["CatchStm", "CatchExceptStm", "ThrowCmd"]


class CatchStm(CodeRule):
    def __init__(self):
        super().__init__("catch", ["KW_catch"])

    def apply(self, b, offset):
        b.add(b.peek() != "." and "except" or "catch")        
        return 1

    
class CatchExceptStm(CodeRule):
    def __init__(self):
        super().__init__("catch", ["KW_catch", "Expression", "Begin", "GlobalType", "ExpressionEnd"])

    def apply(self, b, offset):
        b.add("except Exception as "+b.current(3).name)        
        return offset+1

    
class ThrowCmd(CodeRule):
    def __init__(self):
        super().__init__("throw", ["KW_throw"])
        
    def apply(self, b, offset):
        b.add("raise ")
        
        return 1