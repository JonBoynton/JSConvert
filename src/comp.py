'''jsconvert/comp.py

Provides a library of abstract components that model a javascript source code
document.

Most of the Classes defined in the package are sub-classes of 'CodeEntry'; the
base class for each component type. The entry objects are typically not
instanciated directly. Rather, they are created by a 'CodeFactory' instance
which then builds a DOM (Document Object Model) from a source specification.

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
__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

_STARTS = ' ({['
_ENDS = ')}]'
_SEPS = '.,;:'
_OPERATORS = '+-/*%~^=<>&|!?'
_DELIMS = _STARTS + _ENDS + _SEPS+ _OPERATORS
_COMPS = ("===", "==", "!=", "!==", "<", ">", "<=", ">=")
_ASSIGNS = ("=", "+=", "-=", "*=", "**=", "/=", "|=", "&=", "^=", "%=", ">>=", "<<=")

def _is_class_child(e):
    # Determines if an entry is the child of a class block.
    return e.par and isinstance(e.par.par, Classs)


    
class CodeFactory():
    """Parses javascript source code into a DOM comprised of CodeEntry instances.
    
    The 'src' argument requires a string containing valid javascript source
    code.  The 'keywords' argument requires a function reference having '(keyword,
    parent, offset)' attributes.  The function will create and return a
    CodeEntry instances for various language specific reserved words. If the
    function returns 'None' for a reserved word, a default class of
    'Modifier' will be assigned.
    
    All terms that are not reserved by javascript (ES6), plus punctuation, and
    delimiters are parsed via internal rules of the CodeFactry
    """
    
    def __init__(self, src, keywords):
        self.keywords = keywords
        self.spec = src
        self.length = len(src)
    
    
    def get_code(self):
        """Returns a RootEntry Object parsed from this factories source code. 
        
        This method creates a new RootEntry each time it is called and may be
        expensive.
        """
        root = RootEntry(self)
        try:
            root._pack()
        except:
            pass
        return root
        
    def parse_entry(self, e, c, i):
        """Creates a new 'un-packed' entry with initial properties only.
        
        This method is used by subclasses of CodeEntry when parsing child
        entries.
        e = parent entry 
        c = starting character 
        i = character offset in source string
        """
        st = None 
        
        if not c.isidentifier():
            
            if c == "'" or c == '"' or c == '`':
                st = StringType(e, i)
                
            elif c == "{":
                st = isinstance(e, Expression) and ObjectType(e, i) or StatementBlock(e, i, False)
                
            elif c == "(":
                st = Expression(e, i, not isinstance(e.last_entry(), Assignment))
            
            elif c == "[":
                st = ArrayType(e, i)
                
            elif c == "?":
                st = TernaryExpression(e, i)
                
            elif c == ".":
                st = Separator(e.last_entry(), i, c)
                
            elif c.isdigit() or (c == "-" and 
                self.spec[i+1].isdigit() and not 
                isinstance(e.last_entry(), Extendable)):
                st = NumberType(e, i, c + e._next_token(self.next_char(i+1)))
                
            elif c in _OPERATORS:
                
                op = self._next_op(i)
                
                if op == "=>":
                    st = Lambda(e, i)
                
                elif op.startswith("#"):
                    st = Comment(e, i, op)
                    
                elif op in _COMPS:
                    st = Compare(e, i, op)
                    
                elif op.endswith("="): 
                    st = Assignment(e, i, op)
                    
                elif op == "++" or op == "--":
                    st = Increment(e, i, op)
                    
                elif c == "/" and not e.get_children():
                    st = RegExpression(e, i)
                    
                else:       
                    st = Operator(e, i, op)
                    
            elif c in _SEPS:
                st = Separator(e, i, c)
                
            elif c in _ENDS:
                st = End(e, i, c)
                
            elif c == "@":
                st = Annotation(e, i)
                
            else:
                st = Code(e, i, 1, c)
                            
        elif c:

            tk = e._next_token((c, i))
            st = self.keywords(tk, e, i)

            if not st:
                t = self.next_char(e.pos)
                if t[0] == "(":
                    st = (_is_class_child(e) and Method(e, i, "", tk)) or Function(e, i, tk)
                    
                elif t[0] == ":" and not isinstance(e, Expression):
                    st = Label(e, i, tk)
                    
                elif isinstance(e, Declarable):
                    st = Attribute(e, i, tk)
                    
                elif (tk == "get" or tk == "set") and _is_class_child(e):
                    st = tk == "get" and Getter(e, i) or Setter(e, i)
                    
                elif (isinstance(e.last_entry(), Extendable) or 
                    (isinstance(e, Container) and e or e.get_container()).is_variable(tk)):
                    st =  VariableType(e, i, tk)
                    
                else:
                    st =  GlobalType(e, i, tk)
            
            # Allow rare keyword being used as a class method or Function name
            elif isinstance(st, Modifier) and self.next_char(e.pos)[0] == "(":
                st = Method(e, i, "", tk) if _is_class_child(e) else Function(e, i, tk)
            
        return st

    def next_char(self, offset) -> tuple:
        """Skips over whitespace from the offset position to next printable character.
        
        Returns a tuple with (printable character, position in source).  If the
        end of the source string is reached, the tuple has an empty string and
        source length
        """
        
        for i in range(offset, self.length):
            c = self.spec[i]
            if c.isprintable() and not c.isspace():
                return (c, i)
        
        return ("", self.length)  
     
    def _next_op(self, offset) -> tuple:
        # Appends characters from the starting offset into a complete operator token.
        
        op = ""
        for i in range(offset, self.length):
            if self.spec[i] in _OPERATORS:
                op += self.spec[i]
            else:
                if op.startswith("/*"):
                    op = "#*" # we use a special operator for comments
                elif op.startswith("//"):
                    op = "##"
                break;
        
        return op  
    
    def _is_escaped(self, pos) -> bool:
        # Determines if specified position is preceded by an escape character.
        
        cnt = 0
        while pos > 0 and self.spec.rfind("\\", 0, pos) == pos-1:
            cnt += 1
            pos -= 1
             
        return cnt % 2 == 1


class CodeEntry:
    """CodeEntry is the base class for all DOM components in jsconvert.
    
    A CodeEntry instance identifies a substring representing a code part.  It
    also contains methods for parsing and accessing child components. If an
    entry has, or may have, child components, it's initial substring is empty
    until its '_pack()' method is called.  The '_pack()' method is called
    automatically by CodeFactory.
    """
    def __init__(self, par, offs, name="", factory=None):
        self.cf = factory or par.cf
        self.par = par
        self.offs = offs
        self.pos = offs
        self.name = name    
        self.has_more = False   # indicates if parsing is complete
        self.inset = par and par.inset+1 or 0 # the number of parent entries from root
    
    def _next(self):
        return None
    
    def _try_next(self):
        # Gets the next_char tuple or returns None if no more children or end of source.
        
        if self.has_more:  
            t = self.cf.next_char(self.pos)
            if t[0]:
                return t 
            
            self.has_more = False
            self.pos = t[1]

        return None
    
    def _pack(self):
        # Called to initialize parsing of child entries.
        
        while self.has_more:
            se = self._next()
            
            # note: this is a good place for a debugging trap using se type
            
            if se:
                if se.name == ".":
                    if isinstance(se.par, Extendable):
                        self.pos = se.pos
                        ne = self._next()
                        ne._set_parent(se.par)
                        se.par.extended = ne
                        se = ne                        
                    
                self.push_entry(se)
                se._pack()
                self.pos = se.pos
            else:
                self.has_more = False
           
    def _next_token(self, c=None) -> str:
        # The next full word available when components are being packed
        
        if not c:
            c = self.cf.next_char(self.pos)
            
        if c[0] in _DELIMS: # if delimiter or empty we are done
            return ""
    
        dot = True
        sp = self.cf.spec;
        
        for i in range(c[1]+1, len(sp)):
            ch = sp[i]
            if ch in _DELIMS or ch.isspace() or not ch.isprintable():
                # _skip over likely decimal point
                if ch == "." and dot and c[0].isnumeric() and sp[i+1].isnumeric():
                    dot = False
                    continue
                
                self.pos = i
                return sp[c[1]: self.pos]
            
        self.pos = len(sp)                   
        return sp[c[1]: self.pos] 
             
    def _skip(self, pos):
        # Positions parser after the next non-escaped occurrence of a char at 'pos'.
        
        pos = self.cf.spec.find(self.cf.spec[pos], pos+1)        
        if pos == -1:
            self.pos = self.cf.length
        elif self.cf._is_escaped(pos):
            self._skip(pos)
        else:
            self.pos = pos+1
    
    def _is_start(self):
        # Returns True if the entry is positioned at the first character (before parsing).
        return self.offs == self.pos
    
    def _is_end_char(self, c):
        # Override to return True if the specified character delimits the end of a sequence
        return False
    
    def _set_parent(self, par):
        # Used to extend a parent component
        self.par = par
        self.inset = par.inset+1    

    def is_leaf(self):
        """Returns True if the entry does not have child elements."""
        return isinstance(self, Leaf)
    
    def is_nested(self):
        """Returns True if the parent entry is extended by this entry (has a dot delimiter)"""
        return bool(isinstance(self.par, Extendable) and self.par.extended is self) 
    
    def push_entry(self, entry):
        """Adds a new entry to this components container."""
        self.par.push_entry(entry)
        
    def last_entry(self):
        """Returns the last entry added to this components container"""
        return self.par.last_entry()
    
    def remove_entry(self, ent=None):
        """Removes this entry from its container."""
        self.par.remove_entry(ent or self)
    
    def get_prop(self, name):
        """Gets the unique property name for a declared variable (includes its scope name)."""
        return self.par.get_prop(name)
    
    def get_children(self, entry=None):
        """Returns a list of child components or an empty list if is_leaf."""
        if (entry or self).is_leaf():
            return []

        # propagate request upward to a container instance
        return self.par.get_children(entry or self)
    
    def get_descendants(self):
        da = []
        for c in self.get_children():
            da.append(c)
            da.extend(c.get_descendants())
    
    def get_ancestor(self, clsTyp):
        """Returns the nearest ancestor component with the specified class or None"""
        p = self.par
        while p and not isinstance(p, clsTyp):
            p = p.par
            
        return p

    def get_container(self):
        """The Container entry holding a reference to this component"""
        p = self.par
        while p and not isinstance(p, Container):
            p = p.par
            
        return p

    def get_previous(self):
        """ Returns the previous sibling component that is not a comment; or None"""
        lst = self.get_children(self.par)
        try:
            i = lst.index(self) - 1
            return i > -1 and lst[i] or None
        except:
            return None

    def get_next(self):
        """Returns the next sibling component that is not a comment; or None"""
        lst = self.get_children(self.par)
        try:
            return lst[lst.index(self) + 1]
        except:
            return None
    
    def get_jstype(self):
        return ""
    
    def __str__(self):
        return self.cf.spec[self.offs:self.pos]
    

# An element that holds CodeEnties and declared variables within its scope, also lambda bug
class Container(CodeEntry):
    """The base class for CodeEntry Objects that declare and list descendants."""
                  
    def __init__(self, par, offs, inscope=True, factory=None):
        super().__init__(par, offs, "", factory)
        self.stack = []
        self.has_more = True
        self.ccnt = 0   #child container count
        self.scope = ""
        
        # set the scope name for this container
        p = inscope and par 
        while p:
            if isinstance(p, Container):
                p.ccnt += 1
                self.scope = p.scope + "_" + str(p.ccnt)
                break
            else:
                p = p.par
                
    def entries(self, ea=None):
        """Returns a recursive list of all CodeEntry instances within this container."""
        
        if not ea:
            ea = []
        for e in self.stack:
            ea.append(e)
            if isinstance(e, Container):
                e.entries(ea)
        
        return ea
                
    def push_entry(self, entry):
        if entry:
            self.stack.append(entry)
            
    def last_entry(self):
        for e in reversed(self.stack):
            if not isinstance(e, Comment):
                return e
            
        return None
    
    def remove_entry(self, ent=None):
        if ent:
            try:
                for e in self.get_children(ent):
                    self.remove_entry(e)
                            
                self.stack.remove(ent)
                return
            
            except:
                pass
            
        else:
            self.stack.clear()
            ent = self
            
        if self.par:
            self.par.remove_entry(ent)
        
    def replace_entry(self, oldEntry, newEntry):
        """Replaces an existing CodeEntry with a new one
        
        The new entry will be assigned the same parent entry and inset value as
        the old one. In Addition, the new entry will be set as the parent for
        any children of the old entry.
        """
        try:
            i = self.stack.index(oldEntry)
            for c in oldEntry.get_children():
                c.par = newEntry
                
            newEntry.par = oldEntry.par
            newEntry.inset = oldEntry.inset
            newEntry.cf = oldEntry.cf
                
            self.stack[i] = newEntry
            
        except:
            return False
        
        return True

    # inserts an Entry as the new parent of an existing child entry
    def insert_parent(self, child, parent):
        """Inserts a CodeEntry as the new parent of an existing child entry.
        
        This differs from 'replace_entry' in that the old entry remains in the
        container. Its parent value is set to the new entry while its inset
        value, and the inset of its children, is incremented by one.
        """
        i = self.index_of(child)
        if i == -1:
            return False
        
        parent.par = child.par
        parent.inset = child.inset
        parent.offs = child.offs
        child.par = parent
        child.inset += 1
        
        pos = i+1
        siz = len(self.stack)
        while pos < siz and self.stack[pos].inset > parent.inset:
            self.stack[pos].inset += 1
            pos += 1

        self.stack.insert(i, parent)
        return True
    
    def insert_after(self, oldEntry, newEntry):
        """Inserts a new entry at the index position following an existing entry"""
        
        i = self.index_of(oldEntry)
        if i == -1:
            return False

        self.stack.insert(i+1, newEntry)
        return True 
       
    def get_children(self, entry=None):
        """Creates a list of all child components for the specified entry. 
        
        The specified entry (if any) must be a descendant of this container. If
        not specified, the entry used will be 'self'
        """
        if not entry:
            entry = self 
        
        lst = []
        if not entry.is_leaf():
            i = 0
            if entry is not self:
                i =  self.index_of(entry) + 1
                if not i:
                    return lst
                
            ln = len(self.stack)
            
            # find all stack entries that have 'entry' as a parent and are not comments
            while i < ln and self.stack[i].inset > entry.inset:
                e = self.stack[i]
                if e.par is entry and not isinstance(e, Comment):
                    lst.append(e)
                i += 1
            
        return lst
              
    def get_prop(self, name):
        return name + self.get_scope(name)
    
    def get_scope(self, name):
        """Return the scope value for the specified variable name."""
        
        for se in self.stack:
            if isinstance(se, Declaration) and se.value == name:
                if self.get_container().is_declared(name):
                    return self.scope
                return "" 
        
        return self.get_container().get_scope(name)

    def is_declared(self, name, local=False):
        """Returns True if the specified variable name is declared in this container or an ancestor"""
        
        for se in self.stack:
            if isinstance(se, Declaration) and se.value == name:
                return True

        return (not local and bool(self.par and self.get_container().is_declared(name))) or False

    def is_variable(self, name):
        """Returns True if the specified variable name is a declared variable in
        this container or an ancestor."""
        
        for se in self.stack:
            if isinstance(se, Declaration) and se.is_variable and se.value == name:
                return True

        return bool(self.par and self.get_container().is_variable(name))
    
    # The index of a stack entry or -1 if not found
    def index_of(self, entry):
        """Return the index of a CodeEntry in the containers list or -1 if not found"""
        try:
            return self.stack.index(entry)
        except:
            return -1
    
    def __str__(self):
        return ""
    

class RootEntry(Container):
    """Top level container for the jsconvert DOM."""   
    def __init__(self, factory, offs=0):
        super().__init__(None, offs, False, factory)
        
    def get_container(self):
        return self
    
    def get_scope(self, name):
        return ""
        
    def _next(self):
        t = self._try_next()
        if t:        
            return self.cf.parse_entry(self, t[0], t[1])   

        return None   
    
class Leaf():
    """Tagging class for CodeEntry sub-classes that do not have children."""
    pass    
    
    
class Extendable():
    """Tagging class for CodeEntry sub-classes that can be extended by a variable or function"""
    pass
    
    
class Declarable:
    """Tagging class for CodeEntry sub-classes that declare attributes."""
    pass 
  
  
class Code(CodeEntry, Leaf):
    """A snippet of code with the given length. 
    
    Calling str(Code) returns the entire value
    """
    def __init__(self, par, offs, length, name=""):
        super().__init__(par, offs, name)
        self.pos += length

        
class Separator(Code):
    """A delimiting character between two script elements."""
    def __init__(self, par, offs, c):
        super().__init__(par, offs, len(c), c)
        

#  
class Begin(Separator):
    """The opening character of a script element."""
    def __init__(self, par, offs, c):
        super().__init__(par, offs, c)
        
             
# Tags a Code snippet as the ending of an entry statement. 
class End(Separator):
    """The closing character of a script element."""
    def __init__(self, par, offs, c):
        super().__init__(par, offs, c)
        
        
class FunctionEnd(End, Extendable):
    def __init__(self, par, offs):
        super().__init__(par, offs, ")")
        self.extended = False

        
class ExpressionEnd(End, Extendable):
    def __init__(self, par, offs):
        super().__init__(par, offs, ")")
        self.extended = False

        
class ObjectEnd(End, Extendable):
    def __init__(self, par, offs):
        super().__init__(par, offs, "}")
        self.extended = False

        
class ArrayEnd(End, Extendable):
    def __init__(self, par, offs):
        super().__init__(par, offs, "]")
        self.extended = False

        
class Annotation(Code):
    def __init__(self, par, offs):
        super().__init__(par, offs, 0, "@")
        i = self.cf.next_char(offs+1)
        while i < self.cf.length and not self.cf.spec[i].isspace():
            i += 1
            
        self.pos = i               

class Declaration(CodeEntry, Leaf):
    """An element that identifies a new variable, function, or class.
    
    Sub-classes of Declaration are used to identify scope within a code block.
    The 'name' attribute is the declarations keyword type (if any); such as
    'var' or 'let'.  The 'value' attribute holds the name of the actual variable
    or function being declared.
    """
    def __init__(self, par, offs, name="", value=None):
        super().__init__(par, offs, name) 
        self.pos += len(name)
        self.is_variable = False
        
        if value:
            self.pos += len(value)
            self.value = value
        else:
            self.value = self._next_token()

    def __str__(self):
        return self.name and (self.name+" "+self.value) or self.value
    
    
class Attribute(Declaration):
    def __init__(self, par, offs, value=None):
        super().__init__(par, offs, "", value)
        self.is_variable = True
        
    def __str__(self):
        return self.value

    
class Method(CodeEntry):
    """Identifies a block of code that creates a function or class method."""
    
    def __init__(self, par, offs, name="", value=None):
        super().__init__(par, offs, name)
        self.value = value
        self.has_more = True
        
        
    def _next(self):
        if self._is_start():
            return Declaration(self, self.pos, self.name, self.value)
        
        t = self._try_next()
        self.has_more = False
        return Constructor(self, t[1])
    
    def __str__(self):
        return self.name or ""
        

class Label(Attribute):
    """An attribute followed by a semicolon."""
    
    def __init__(self, par, offs, name=""):
        super().__init__(par, offs, name)
        if not name:
            self.pos += len(self.value)
        # self.pos = par.cf.spec.find(':', self.pos)+1


# A list of statements, functions, and comments bound by beginning and ending delimiters
class Block(CodeEntry):
    """A list of components bound by beginning and ending delimiters."""
    
    def __init__(self, par, offs, begin="{", end="}"):
        super().__init__(par, offs)
        self.begin = self.cf.spec[self.offs] == begin and begin or None
        self.end = end
        self.has_more = True
        
    @property
    def is_enclosed(self):
        """Returns True if a Block instance has both opening and closing characters."""
        return bool(self.begin)
            
    def _is_end_char(self, c):   
        if self.begin:
            return c == self.end
            
        return c == ";"
    
    def _next(self):
        if self._is_start() and self.begin:
            return Begin(self, self.offs, self.begin)
            
        t = self._try_next()
        if t:        
            if self._is_end_char(t[0]):
                if self.begin:
                    self.has_more = False
                    return End(self, t[1], self.end)
                    
            else:
                return self.cf.parse_entry(self, t[0], t[1])   

        return None
    
    def __str__(self):
        return ""
        

class StatementBlock(Container):
    """A Container instance that holding the components of a Statement or Class.
    
    Typically, a StatementBlock represents the components within curly braces {...} 
    following a Statement keyword; such as 'if'. It does not include the statements
    condition arguments (if any).
    """
    def __init__(self, par, offs, inscope=True):
        super().__init__(par, offs, inscope)
        self.extended = False
        
    def _next(self):
        if self._is_start():
            return Block(self, self.offs)       
            
        return None  
    
    def get_jstype(self):
        return "object"
    
  
class ImportBlock(Block):
    def __init__(self, par, offs, root=True):
        super().__init__(par, offs, not root and '{' or None)
        
    def _next(self):
        if self._is_start() and self.begin:
            return Begin(self, self.offs, self.begin)
            
        t = self._try_next()
        st = None
        
        if t:
            c = t[0]
            tp = t[1]       
                   
            if self._is_end_char(c):
                if self.begin:
                    self.has_more = False
                    st = End(self, tp, self.end)
                    
            else:
                st = self.cf.parse_entry(self, c, tp)
                if st:                    
                    if st.name == "as":
                        pr = self.last_entry()
                        pr.get_container().replace_entry(pr, NameType(self, pr.offs, pr.value))
                        
                    elif isinstance(st, VariableType):
                        st = Attribute(self, tp, st.name)
                        
                    elif isinstance(st, StatementBlock):
                        st = ImportBlock(self, tp, False)

        return st 

    
class Constructor(Container, Declarable):
    """A block of code that creates function or method"""
    
    def __init__(self, par, offs, sep=","):
        super().__init__(par, offs, False)
        self.inblock = False
        self.sep = sep
        
    def _next(self):
        if self._is_start():
            return Begin(self, self.pos, "(")
        
        st = None   
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]       
            
            if self.inblock:
                self.has_more = False
                st = Block(self, tp) 
                
            elif c == self.sep:
                st = Separator(self, tp, c)
                
            elif c == ")":
                self.inblock = True
                st = End(self, tp, ")")
                
            else:
                st = self.cf.parse_entry(self, c, tp)
            
        return st

    
class Expression(Block):
    
    delims=")}];,:"
    
    def __init__(self, par, offs, bound=True):
        super().__init__(par, offs, bound and "(" or "", ")")
    
    def _is_end_char(self, c):   
        if self.begin:
            return c == self.end
            
        return c in self.delims  
    
    def _next(self):
        if self._is_start() and self.begin:
            return Begin(self, self.offs, self.begin)
            
        t = self._try_next()
        if t:        
            if self._is_end_char(t[0]):
                if self.begin:
                    self.has_more = False
                    return ExpressionEnd(self, t[1])
                    
            else:
                return self.cf.parse_entry(self, t[0], t[1])   

        return None   
                
    
class Assignment(CodeEntry):
    """Identifies a code fragment that assigns a value to a variable."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        self.has_more = True
            
    def _next(self):
        if self._is_start():
            return Operator(self, self.pos, self.name)
        
        self.has_more = False
        return Expression(self, self.cf.next_char(self.pos)[1], False)
    
    
class Increment(Assignment):
    """Identifies a code fragment that increments a value by 1 or -1."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        self.has_more = True
        self.lefthand = False
            
    #               
    def is_left_hand(self):
        """Returns True if the increment operator is on the left side of a variable."""
        
        return self.lefthand
        
    def _next(self):
        if self._is_start():
            p = self.get_previous()
            if isinstance(p, VariableType):
                while isinstance(p.par, VariableType) and p.par.extended is p:
                    p = p.par
                    
                self.remove_entry()
                self.get_container().insert_parent(p, self)
                self.has_more = False
            else:
                self.lefthand = True
                
            return Operator(self, self.pos, self.name)
        
        self.has_more = False    
        v = self._next_token()
        return VariableType(self, self.pos - len(v), v)
        
        
class Function(CodeEntry):
    """Identifies a callable statement."""
    
    functional = True
        
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        self.has_more = True
        self.inblock = False
        
        
    def _next(self):
        if self._is_start():
            return NameType(self, self.pos, self.name)

        st = None
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]
            
            if c == ")":
                self.has_more = False
                st = FunctionEnd(self, tp)
            
            elif not self.inblock:
                self.inblock = True
                st = Begin(self, tp, "(")
            
            elif c == ",":
                st = Separator(self, tp, c)
                
            else:
                st = Expression(self, tp, False)
            
        return st
    
    
    def __str__(self):
        return ""
    
class Lambda(Container, Declarable):
    """Identifies a block of code that encapsulates a Lamda Expression."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs, False)
        
        last = par.last_entry()
        
        if isinstance(last, VariableType):
            self.bounded = False
        
        elif isinstance(last.par, Expression):
            last = last.par
            self.bounded = bool(last.begin)            
        
        else:
            raise SyntaxError("Invalid Lambda constructor")
        
    #bug: last was not removed        
        last.remove_entry() 
    
        self.initOffs = offs
        self.offs = last.offs
        self.pos = last.offs
        
    def _next(self):
        if self._is_start() and self.bounded:
            return Begin(self, self.pos, "(")
        
        st = None    
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]       
            
            if self.pos > self.initOffs:
                self.has_more = False
                st = c == "{" and Block(self, tp) or Expression(self, tp)
            
            elif tp == self.initOffs:
                st = Operator(self, tp, "=>")
                
            elif c == ")":
                st = End(self, tp, ")")
            
            elif c == ",":
                st = Separator(self, tp, ",")
                
            else:
                st = self.cf.parse_entry(self, c, tp)
            
        return st 
    
    
class Statement(CodeEntry):
    """Identifies a block of code named by a keyword."""
    
    def __init__(self, par, offs, name=""):
        super().__init__(par, offs, name)
        self.pos += len(name)
        self.has_more = True
        
    def _is_start(self):
        return self.offs + len(self.name) == self.pos
    
    def __str__(self):
        return self.name
    

class Condition(Statement):
    """A Statement that evaluates a boolean Expression before executing a StatementBlock."""
    
    functional = True
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        
    def _next(self):
        t = self._try_next()
        if t:
            if self._is_start():
                return Expression(self, t[1])
        
            if t[0] == ";":
                return None
            
            elif t[0] == "{":
                self.has_more = False
                
            return StatementBlock(self, t[1], True)
        
        return None

    
class ForCondition(Container):
    """Encapsulates the initializing block of code within a 'for' loop."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs)
        self.inblock = False    
        
    def _next(self):
        st = None   
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]       
            
            if self.inblock:
                if c != ";":  
                    self.has_more = False
                    st = Block(self, tp) 
                
            elif c == "(":
                st = Begin(self, tp, c)
                
            elif c == ";":
                st = Separator(self, tp, c)
                
            elif c == ")":
                self.inblock = True
                st = End(self, tp, c)
                
            else:
                st = Expression(self, tp, False)
            
        return st  
    
    def __str__(self):
        return ""  


class TernaryExpression(Expression):
    """Identifies a three part conditional expression utilizing '?' and ':' separators."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs, False)

        last = par.last_entry()
        bgn = None
        
        if last.name == ")":
            last = last.par
        
        if not isinstance(last, Expression):
            last = last.get_ancestor(Expression)
            if last.begin:
                bgn = last.get_children()[0]

        self.pos = offs
        self.inblock = False 
        last.get_container().insert_parent(last, self) 
            
        if bgn and bgn.name == "(":
            bgn.remove_entry()
            bgn.par = self
            bgn.inset = self.inset+1
            self.begin = last.begin
            last.begin = None
            self.get_container().insert_after(self, bgn)

    def _next(self):
        st = None    
        t = self._try_next()

        if t:        
            c = t[0]
            tp = t[1]       

            if c == "?":
                self.get_container().stack.pop() # hack - prevents double entry
                self.inblock = True
                st = Operator(self, tp, c)
                
            elif c == ":":
                self.inblock = False
                st = Separator(self, tp, c)
                
            elif self.begin and self._is_end_char(c):
                self.has_more = False
                return End(self, t[1], self.end)
            else:
                self.has_more = bool(self.inblock or self.begin)
                st = Expression(self, tp, False)

        return st     

class RegExpression(CodeEntry, Leaf):
    def __init__(self, par, offs):
        super().__init__(par, offs)
        if par.cf.spec[offs] != "/":
            raise TypeError("Not Regular Expression")
        
        self._skip(offs)
        self._next_token()  
               

class VariableType(CodeEntry, Extendable):
    """Identifies the name of variable or class."""
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        self.pos += len(name)
        self.prefix = self.get_prop
        self.extended = False

    def is_leaf(self):
        return not self.extended
    
    def get_extent(self):
        """The number of components in a dot delimited chain; beginning with this one."""
        
        cnt = 1
        e = self.extended
        while e:
            cnt += 1
            e = e.extended
            
        return cnt
           
    def value_of(self):
        return self.name
            
    def _set_parent(self, par):
        super()._set_parent(par)
        if isinstance(par, Extendable):
            self.prefix = lambda nm: nm
    
    def get_local_name(self):
        """The unique name of this variable after applying the local scope"""
        
        return self.prefix(self.name)  
    
    def get_full_name(self):
        """The complete dot delimited name of the entry; including ancestors and descendant variables."""
        
        if isinstance(self.par, VariableType) and self.par.extended is self:
            return self.par.get_full_name()  
        
        nm = self.get_local_name()
        c = self.extended
        while c:
            nm += "."+c.name
            c = c.extended
            
        return nm   
                                   
    def __str__(self):
        return self.name
    
        
class NameType(VariableType, Leaf):
    """Identifies the name of a function."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)

    def value_of(self):
        return self.name
        
        
class GlobalType(VariableType, Leaf):
    """Identifies the name of an automatically imported or built-in variable."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)

    def value_of(self):
        return self.name
    

class StringType(CodeEntry, Extendable):
    """Encapsulates a string argument (including quotes)."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs)
        self._skip(offs)
        self.extended = False
        
    def is_leaf(self):
        return not self.extended
            
    def get_jstype(self):
        return "string"
        
    def value_of(self):
        """The un-quoted string value."""
        
        if self.pos-2 > self.offs:
            return self.cf.spec[self.offs+1 : self.pos-1]
        
        return ""
    
        
class NumberType(CodeEntry, Extendable):
    """Encapsulates a number argument."""
    
    def __init__(self, par, offs, value="0"):
        super().__init__(par, offs)
        self.pos += len(value)
        self.extended = False
        
    def is_leaf(self):
        return not self.extended
    
    def value_of(self):
        """The number as an 'int' or 'float' value."""
        
        n = str(self)
        return n.find(".") != -1 and float(n) or int(n)

    def get_jstype(self):
        return "number" 
    
       
class BooleanType(CodeEntry, Extendable):
    def __init__(self, par, offs, value=True):
        super().__init__(par, offs, value and "true" or "false")
        self.pos += value and 4 or 5
        self.extended = False
        
    def is_leaf(self):
        return not self.extended
    
    def value_of(self):
        """The 'bool' value."""
        
        return self.name == "true"
            
    def get_jstype(self):
        return "boolean"
            
    def __str__(self):
        return self.name


class ArrayType(CodeEntry):
    """Encapsulates an array of values."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs)
        self.has_more = True
        
    def _next(self):
        if self._is_start():
            return Begin(self, self.offs, "[")
        
        st = None   
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]
        
            if c == "]":
                self.has_more = False
                st = ArrayEnd(self, t[1])
                
            elif c == ",":
                st = Separator(self, tp, ",") 
            
            else:
                st = Expression(self, tp)
        
        return st;
    
    def __str__(self):
        return ""
    
    def get_jstype(self):
        return "array"

    
class ObjectType(Container):
    """Encapsulates a map of key/value pairs."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs, False)
        self.has_more = True
    
    def _next(self):
        if self._is_start():
            return Begin(self, self.offs, "{")
            
        st = None   
        t = self._try_next()
        
        if t:        
            c = t[0]
            tp = t[1]
                  
            if c == "}":
                self.has_more = False
                st = ObjectEnd(self, tp)
                
            elif c == ":":
                field = self.last_entry()
                ex = field.get_ancestor(Expression)
                self.remove_entry(field)
                self.replace_entry(ex, field)
                st = Separator(self, tp, ":")
                
            elif c == ",":
                st = Separator(self, tp, ",")
                
            else:
                st = Expression(self, tp, False) 

        return st    
        
    def __str__(self):
        return ""    

# Add support for TemplateLiteral
#    
# class TemplateLiteral(Container): # this could have a prefix function
#     """Encapsulates a set of literal arguments."""
#
# class TString(Container):
#     """The character data of a template segment"""
#
# class TExpression(Container):
#     """Encapsulates an expression within template"""

        
class Keyword(CodeEntry, Leaf):
    """A stand alone reserved word."""
    
    def __init__(self, par, offs, length, name):
        super().__init__(par, offs, name)
        self.pos += length
        
    def __str__(self):
        return self.name or ""
        
       
class Modifier(Keyword):
    def __init__(self, par, offs, name):
        super().__init__(par, offs, len(name), name)

    
class Operator(CodeEntry, Leaf):
    """Any symbol used for mathematical, comparison, or assignment purposes."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)
        self.pos += len(self.name)
                
    def __str__(self):
        return self.name


class Compare(Operator):
    """Any symbol used for comparison purposes."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name)   
    

class Comment(CodeEntry, Leaf):
    """A comment string (with delimiter)."""
    
    def __init__(self, par, offs, name):
        super().__init__(par, offs, name.replace("#","/"))
        i = offs+len(self.name)
        
        if self.name == "/*":
            i = par.cf.spec.find("*/", i)
            self.pos = i + 2 if i != -1 else len(par.cf.spec)
        else:
            i = par.cf.spec.find("\n", i)
            self.pos = i if i != -1 else len(par.cf.spec)

    
    def noEdit(self):
        """Returns True if a Comment contains the singular command 'no-edit'
        
        Transcoders may use the 'no-edit' command to identify files, or blocks
        of code, that should be ignored or not translated.
        """
        return self.cf.spec[self.offs+2:self.pos].strip() == "no-edit"
        
    
class Classs(CodeEntry):
    """Identifies a block of code that defines a Class Object."""
    
    def __init__(self, par, offs):
        super().__init__(par, offs, "class")
        self.has_more = True
               
    def _next(self):
        if self._is_start():
            return Declaration(self, self.pos, "class")
        
        t = self._try_next()
        st = self.cf.parse_entry(self, t[0], t[1])
        
        if isinstance(st, StatementBlock):
            self.has_more = False
        
        return st 

    
class Getter(Method):
    def __init__(self, par, offs):
        super().__init__(par, offs, "get") 

        
class Setter(Method):
    def __init__(self, par, offs):
        super().__init__(par, offs, "set") 
        

    
EMPTY = CodeEntry(None, 0, "", CodeFactory("", None))


        
        