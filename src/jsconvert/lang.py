'''jsconvert/lang.py

Provides concrete implementations of jsconvert DOM components for modeling
javascript keywords.

Keywords are created as subclasses of various CodeEntry components.  By default,
reserved keywords that do not have a specific class are created using the
Modifier class in jsconvert.comp.  Classes can be added to this module as
needed. However, one should be mindful that adding new words may break parser
rules that rely on a generic component names.  Also, new words should be
somewhat unique and not ambiguous.

As a convention, classes are named by using the word they identify as a suffix.
Words reserved by javascript are prefixed with 'KW_'. Words that are part of the
'built-in' library (including functions), should be prefixed with 'BW_'. Words that
are neither reserved or keywords are identified with the prefix 'XW_'.

In rare cases, the same word may be expresses with two different class prefixes.
In such case, one must identify a callable statement or function.  The other
must not.

Additional documentation can be found at DataMessenger.com:
    http://www.datamessenger.com/

Created on Nov 16, 2021

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

from jsconvert.comp import (Modifier, 
    Keyword, 
    Condition, 
    Statement, 
    Declaration,
    ImportBlock, 
    Method, 
    ForCondition, 
    StatementBlock, 
    BooleanType, 
    VariableType,
    Expression, 
    End,
    Classs)

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"


# Words reserved by the javascript language (ES6) + undefined
JS_KEYWORDS = (
    "abstract", "arguments", "as", "await", "boolean", "break", "byte", "case", "catch", 
    "char", "class", "const", "continue", "constructor", "debugger", "default", "delete", "do", 
    "double", "else", "enum", "eval", "export", "extends", "false", "final", 
    "finally", "float", "for", "from", "function", "goto", "if", "implements", "import", 
    "in", "instanceof", "int", "interface", "let", "long", "native", "new", "null", "of",
    "package", "private", "protected", "public", "return", "short", "static", 
    "super", "switch", "synchronized", "this", "throw", "throws", "transient", 
    "true", "try", "typeof", "var", "void", "volatile", "while", "with", "yield", "undefined")



class Keywords():
    """Factory class used to create CodeEntry instances given a keyword token.
    
    Instances of this class are used by the transpiler when parsing the
    jsconvert DOM.  However, any Object implementing a 'get_code_instance(name,
    par, offs)' function can be used instead. By default, the Keywords class
    will load all global classes beginning with the prefix 'KW_' or 'XW_'.   
    """
    
    keys = None
    altkeys = None
    
    def __init__(self):
        if not self.keys:
            keys = {}
            altkeys = {}
            nm = None
            
            for e in globals().items():
                if (e[0].startswith("KW_") or 
                    e[0].startswith("XW_")): # key_word or extension_word
                    nm = e[0][3:]
                    
                    if keys.get(nm):
                        if hasattr(e[1], "functional"):
                            altkeys.update({nm: keys.get(nm)})
                        else:
                            altkeys.update({nm: e[1]})
                            continue
                        
                    keys.update({nm: e[1]})
                    
            for nm in JS_KEYWORDS:
                if not keys.get(nm):
                    keys.update({nm: self._def_mod(nm)})
                    
            self.keys = keys
            self.altkeys = altkeys
            
    def _def_mod(self, nm):
        return lambda p, i : Modifier(p, i, nm)
    
    def get_code_instance(self, keyword, par, offs):
        """Creates a CodeEntry instance of a DOM component using a keyword.
        
        The component created is matched to the specified keyword and will have
        the specified parent component and source offset. By default, if the
        keyword is a javascript reserved word but does not have an associated
        class, an instance of 'Modifier' is returned. If the keyword is in
        valid, this method returns 'None'.
        """
        c = self.keys.get(keyword)
        if c:
            if hasattr(c, "functional") and par.cf.next_char(offs+len(keyword))[0] != '(':
                c = self.altkeys.get(keyword)
                return c and c(par, offs) or None
            
            return c(par, offs)
        
        return None
    

class KW_export(Modifier):
    def __init__(self, par, offs):
        super().__init__(par, offs, "export")
        

class KW_import(ImportBlock):
    def __init__(self, par, offs):
        super().__init__(par, offs)

    def _next(self):
        if self._is_start():
            return Keyword(self, self.offs, 6, "import")

        return super()._next()

# class KW_import(ImportBlock):
#     def __init__(self, par, offs):
#         super().__init__(par, offs)
#
#     def _next(self):
#         if self._is_start():
#             return Keyword(self, self.offs, 6, "import")
#
#         t = self._try_next()
#         self.has_more = False
#
#         return (t and ImportBlock(self, t[1])) or None 
    
    
class KW_from(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 4, "from") 
        

class KW_default(Modifier):
    def __init__(self, par, offs):
        super().__init__(par, offs, "default")
        
               
class KW_if(Condition):
    def __init__(self, par, offs):
        super().__init__(par, offs, "if") 
            

class KW_else(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs, "else")
        
    def _next(self):
        t = self._try_next()
        self.has_more = False
        return self.cf.parse_entry(self.par, t[0], t[1])
    

class KW_for(Statement):
    functional = True
    
    def __init__(self, par, offs):
        super().__init__(par, offs, "for")

    def _next(self):
        if self._is_start():
            return ForCondition(self, self.pos)

        return None 

        
class KW_do(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs, "do")
        
    def _next(self):
        self.has_more = False
        return StatementBlock(self, self.cf.next_char(self.pos)[1]) 
           
    
class KW_while(Condition):
    def __init__(self, par, offs):
        super().__init__(par, offs, "while")
        
    
class KW_switch(Condition):
    def __init__(self, par, offs):
        super().__init__(par, offs, "switch")
        
        
class KW_case(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs, "case")
        self.has_more = True
        
    def _next(self):
        t = self._try_next()
        if t:            
            if t[0] == ':':
                self.has_more = False
                return End(self, t[1], t[0])
            
            return Expression(self, t[1], False)
        
        return None

    
class KW_extends(Declaration):
    def __init__(self, par, offs):
        super().__init__(par, offs, "extends")
           

class KW_break(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 5, "break") 
        

class KW_continue(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 8, "continue") 
        

class KW_function(Method):
    def __init__(self, par, offs):
        super().__init__(par, offs, 'function') 


class KW_var(Declaration):
    def __init__(self, par, offs):
        super().__init__(par, offs, "var")
        self.is_variable = True
        

class KW_let(Declaration):
    def __init__(self, par, offs):
        super().__init__(par, offs, "let")
        self.is_variable = True
        

class KW_const(Declaration):
    def __init__(self, par, offs):
        super().__init__(par, offs, "const")
        self.is_variable = True 
        
        
class KW_true(BooleanType):
    def __init__(self, par, offs):
        super().__init__(par, offs, True) 
        
        
class KW_false(BooleanType):
    def __init__(self, par, offs):
        super().__init__(par, offs, False) 
        
        
class KW_constructor(Method):
    functional = True
    
    def __init__(self, par, offs):
        super().__init__(par, offs, "", "constructor")
        

class KW_new(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 3, "new") 
        

class KW_this(VariableType):
    def __init__(self, par, offs):
        super().__init__(par, offs, "this")


class KW_super(VariableType):
    def __init__(self, par, offs):
        super().__init__(par, offs, "super")
    

class KW_try(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs,"try") 
        
    def _next(self):
        self.has_more = False
        return StatementBlock(self, self.cf.next_char(self.pos)[1])
    

class KW_catch(Condition):
    def __init__(self, par, offs):
        super().__init__(par, offs, "catch")
         
# Alternate catch with no condition        
class XW_catch(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs,"catch") 
        
    def _next(self):
        self.has_more = False
        return StatementBlock(self, self.cf.next_char(self.pos)[1])
            

class KW_finally(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs,"finally") 
        
    def _next(self):
        self.has_more = False
        return StatementBlock(self, self.cf.next_char(self.pos)[1])


class KW_throw(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs, "throw")
        
    def _next(self):
        if self._is_start():
            self.has_more = False
            return Expression(self, self.pos, False)
        
        return None 
            

class KW_null(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 4, "null") 

    
class KW_return(Statement):
    def __init__(self, par, offs):
        super().__init__(par, offs, "return")
        
    def _next(self):
        if self._is_start():
            if self.cf.next_char(self.pos)[0] != ';':
                self.has_more = False
                return Expression(self, self.pos, False)
        
        return None 


class KW_class(Classs):
    def __init__(self, par, offs):
        super().__init__(par, offs)

        
class KW_typeof(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 6, "typeof")
        
     
class KW_instanceof(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 10, "instanceof")
        

class KW_undefined(Keyword):
    def __init__(self, par, offs):
        super().__init__(par, offs, 9, "undefined")
