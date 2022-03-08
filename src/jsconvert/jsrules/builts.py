'''jsconvert/jsrules/builts.py

Provides code rules containing special heuristics for transpiling of various
built-in javascript functions and classes into javascript (ES6) source code.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Dec 28, 2021

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

__all__ = ['MathType']


class MathType(CodeRule):
    def __init__(self):
        super().__init__("math", ["BW_Math"])
        
    def apply(self, b, offset):
        c = b.current()
        b.add(c.name)
        if c.extended:
            b.add(".")           
        return 1
