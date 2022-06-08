'''jsconvert/transpiler.py

This module supports the transpiling of javascript (ES6) source code into Python
and other Languages.

Default packages are included for transpiling to python. For testing, packages
are also included for transpiling back to javascript. The transpiling rules may
be modified and extended as needed. Additional rules may be created to support
transpiling to other Languages.

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

from pathlib import Path
from importlib import import_module
from jsconvert.comp import  CodeFactory, CodeEntry, Attribute, StringType, Container, Comment, EMPTY, Block, End
from jsconvert.lang import Keywords, KW_import

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

def _loadFiles(dir_, ext=".js", files=None):
    """Creates a list of files by recursing a file director.
    
    Files returned are filtered by the specified extension 'ext' (optional). The defaul
    extension is '.js'. If 'dir_' is an ordiary file, it will be returned alone in the list.
    """
    if files == None:
        files = []
        
    if dir_.is_dir():
        for f in dir_.iterdir():
            if f.suffix == ext and f.stem != "index":
                files.append(f)
            elif f.is_dir():
                _loadFiles(f, ext, files)
                
    elif dir_.suffix == ext and dir_.stem != "index":
        files.append(dir_)
        
    return files 

def _loadDir(dir_, recurse=False, files=None):
    """Creates a list of files by recursing a file director.
    
    Files returned are filtered by the specified extension 'ext' (optional). The defaul
    extension is '.js'. If 'dir_' is an ordiary file, it will be returned alone in the list.
    """
    if files == None:
        files = []
        
    if not dir_.is_dir():
        dir_ = dir_.parent
        
    for f in dir_.iterdir():
        if f.is_dir():
            files.append(f)
            if recurse:
                _loadDir(f, True, files)
        
    return files 


def _default_string(entry):
    s = not isinstance(entry, Block) and str(entry) or ""
    if len(s) > 40:
        s = s[:40]+"..."
        
    nm = type(entry).__name__
    if len(nm) > 3 and nm[2] == "_":
        nm = nm[3:] + ":" + type(entry).__mro__[1].__name__
        
    return "\t".expandtabs(
        max((entry.inset-1)*4, 0))+"<"+nm+">: "+s.replace("\n", " ")


def _get_ext(ruleset):
    rm = import_module(ruleset, "jsconvert")
    return {
        "input": hasattr(rm, "INPUT_FILE_EXTENSION") and rm.INPUT_FILE_EXTENSION or ".js",
        "output": hasattr(rm, "OUTPUT_FILE_EXTENSION") and rm.OUTPUT_FILE_EXTENSION or ".py",
        "dom": hasattr(rm, "DOM_FILE_EXTENSION") and rm.DOM_FILE_EXTENSION or ".dom",
        }

        
class RuleBucket():
    """Provides a hierarchical directory for matching and processing code rules."""
    
    def __init__(self):  
        self._map = dict(())
        self._list = []

            
    def _add(self, name):
        """Adds a new RuleBucket with the specified name.
        
        Returns the new bucket if created or the old bucket if it already
        existed.
        """
        e = self._map.get(name)
        if not e:
            e = name != "ANY" and RuleBucket() or AnyBucket()
            self._map.update({name: e})
            
        return e

    def process(self, buffer, offs=0):
        """Evaluates the CodeEntry at the current buffer position + offs."""
        
        pos = buffer.offset + offs
        if pos < buffer.size:
            b = self._map.get(type(buffer.entries[pos]).__name__)
            
            if b and b.process(buffer, offs+1):
                return True
            
            b = self._map.get("ANY")
            
            if b and b.process(buffer, offs+1):
                return True
        
        try:    
            for itm in self._list:
                i = itm.apply(buffer, offs-1)
                if i:
                    buffer.offset += i
                    return True
                
        except Exception as err:
            raise RuleProcessingException(err, buffer, itm, buffer.current(), buffer.current(offs-1))
            
        
        # advance to next entry if not handled by any Rule   
        if self is buffer.rules:
            buffer.offset += 1
            return True
           
        return False
        

class AnyBucket(RuleBucket):
    """Variation of RuleBucket for evaluating all child components of a buffer entry."""
    
    def process(self, buffer, offs=0):
        offs -= 2 # resets cursor offset to select the entry before <ANY> 
        c = buffer.current(offs)
        
        # iterate through the children of selected entry
        for c in c.get_children():
            # skip over descendants of child in the buffer stack
            while buffer.entries[buffer.offset + offs] is not c:
                offs += 1
                
            if super().process(buffer, offs):
                return True
            offs += 1
                      
        return False
    
class RuleManager(RuleBucket):
    """Maintains a collection of code rules for transcribing source files.
    
    This manager is constructed using the name of a module that contains
    CodeRule classes.  Classes and sub-modules are identified by the '__all__'
    property.  Classes not listed in '__all__' are ignored. The module will be
    recursively scanned for additional modules and packages.  In addition, an
    optional Keywords object can be provided to create alternate DOM schemes.
    """
    
    def __init__(self, module="", keywords=Keywords().get_code_instance):
        super().__init__()
        self._keywords = keywords
        if module:
            self.add_rules(module)
            
    def add_rules(self, moduleName):
        """Adds a module of CodeRule classes to this manager."""
        
        for r in list_rules(moduleName):
            self.add_rule(r)
        
    def add_rule(self, rule):
        """Adds a single CodeRule instance to this manager."""
        
        b = self
        for e in rule.path():
            b = b._add(e)
            
        b._list.append(rule)    

    
class NoEditException(Exception):
    """Raised during transpiling to prevent overwriting a working document."""
    
    def __init__(self, msg="No-Edit"):
        super().__init__(msg)
        
class RuleProcessingException(Exception):
    def __init__(self, err, buffer, rule, start, end):
        super().__init__("RuleProcessingException: '"+rule.name + \
                        "' near " + _default_string(start).strip())
        
        self.err = err
        self.buffer = buffer
        self.rule = rule
        self.start = start
        self.end = end
        
    def printStack(self):
        if isinstance(self.err, RuleProcessingException):
            self.err.printStack()
            
        print(self.message + "\n")
    
    @property
    def message(self):
        
        st = self.__str__() + \
            (" /.../\n" + _default_string(self.end).strip() if self.start is not self.end else "") + \
            " at chars " +str(self.start.offs) + \
            " to " + str(self.end.pos)
        
        if not isinstance(self.err, RuleProcessingException):            
            st += ";\n"+str(self.err)
            
        return st
        

            
class CodeBuffer():
    """CodeBuffer maintains a linear index of DOM components that will be transpiled to
    a list of strings.
    
    The 'source' argument may be a javascript source code string or a CodeEntry instance.
    The 'rules' argument is a RuleManager instance.
    The buffer is responsible for maintaining an index pointer as transpiling progresses.
    In addition, it provides various methods for evaluating and manipulating the DOM. The
    buffer is the primary tool used by CodeRule objects to examine and append transpiled code.
    """
    def __init__(self, source, rules):
        
        if not isinstance(source, CodeEntry):
            source = CodeFactory(str(source), rules._keywords).get_code()
            
        source._pack()
        self.buf = []
        self.offset = 0
        self.entries = []
        self.rules = rules
        self.heading = None
        self.import_map = None
        self.pb = None # parent buffer (if any)
        self.par_offs = 0 # starting offset for a slice
        self.head_offs = 0 # header insert position
        self.inobject = False # if buffer is inside an object type
        self.inset = 0
        importing = False
        # self.comments = comments # preserve comments in code
        
        if isinstance(source, Container):
            self.heading = HeadingBuffer(self)
            self.import_map = ImportMap()
            
            if (source.stack and 
                isinstance(source.stack[0], Comment) and 
                source.stack[0].noEdit()):
                raise NoEditException()
                
            for e in source.entries():
                if not isinstance(e, Comment):
                    self.entries.append(e)
                    
                if importing and e.name == ";":
                    # reg after finished loading
                    self.size = len(self.entries)
                    self.import_map._register_import(importing, self)
                    importing = False
                        
                elif isinstance(e, KW_import):
                    importing = e
                
        self.size = len(self.entries)
        
    def transpile(self):
        """Fully processes the un-translated components and returns the result as a list of strings."""

        while self.offset < self.size:
            self.rules.process(self)

        return self.buf
    
    def get_slice(self, bgn, end):
        """creates an new instance of this buffer with a slice of indexed components."""
        
        cb = CodeBuffer(EMPTY, self.rules)
        if bgn < end:
            cb.entries = self.entries[bgn:end]
            cb.size = end - bgn
            
        cb.inset = self.inset
        cb.heading = self.heading
        cb.import_map = self.import_map
        cb.pb = self
        cb.par_offs = bgn
        cb.inobject = self.inobject
        return cb
    
    # def get_super_buffer(self, start, end=None):
        
    def get_sub_buffer(self, start, end=None):
        """Creates a buffer from a subset of descendant components.
        
        The 'start' component is not included in the sub-buffer.  If an 'end'
        component is specified, the buffer will be truncated (excluding the
        end).
        """
        try:
            ofs = self.entries.index(start)+1
            i = ofs
            while i < self.size and self.entries[i].inset > start.inset and self.entries[i] is not end:
                i += 1
            
            return self.get_slice(ofs, i)            
        except:
            return self.get_slice(0, 0)

    def add(self, token):
        """Adds a string token to the buffer."""
        
        self.buf.append(token)
    
    def append_entry(self, e):
        """Adds a CodeEntry and its children to the end of this buffer and returns the number
         of components added"""
        
        sb = self.get_sub_buffer(e)
        sb.entries.insert(0, e)
        sb.size += 1
        return self.append_buffer(sb)   

    def append_buffer(self, cb):
        """Transpiles the specified CodeBuffer and adds the result to the end of this buffer.
        
        Returns the number of components added from the input buffer."""
        
        if not cb.entries:
            return 0
        
        # PYTHON BUG: self.buf.extend(cb.transpile()) did not extend first time through
        # maybe 'extend' times-out if function does not return immediately?
        cb.transpile()
        self.buf.extend(cb.transpile())
        return cb.size
    
    def peek(self):
        """Looks at the last string token added to the buffer without removing it."""
        i = len(self.buf)
        return i > 0 and self.buf[i-1] or (self.pb and self.pb.peek() or "")

    def current(self, offset=0):
        """Returns the CodeEntry at the current index position, + or - an optional offset."""
        
        offset += self.offset
        
        if offset >= 0 and offset < self.size:
            return self.entries[offset]
        
        if self.par_offs:
            return self.pb.current((self.par_offs - self.pb.offset) + offset)
        
        return EMPTY

    def next(self):
        """Returns the CodeEntry at the current index position + 1."""
        
        return self.current(1)
    
    def prev(self):
        """Returns the CodeEntry at the current index position - 1."""
        
        return self.current(-1)
    
    def indent(self, offset=0):
        """Returns a string of space characters representing the current tab inset + offset."""
        if offset:
            return "\t".expandtabs(max(self.inset + offset, 0) * 4)
         
        return self.inset and "\t".expandtabs(self.inset*4) or ""
    
    def new_line(self, tabs=0):
        """Appends a new line character, followed by tab spaces, to the buffer.
        
        A tab is four space characters.  The number of tabs is adjusted up or
        down by the optional tabs parameter.
        """
        
        if tabs:
            self.inset = max(0, self.inset + tabs)
        self.buf.append("\n" + self.indent())
    
    def space(self):
        """Appends a single space character to the buffer if there is not already a space."""
        
        if self.buf and self.buf[len(self.buf)-1].isspace():
            return
        
        self.buf.append(" ")
    
    def trim(self):
        """Removes all whitespace from the end of the buffer."""
        
        ln = len(self.buf)-1
        while ln != -1 and (self.buf[ln].isspace() or not self.buf[ln]):
            self.buf.pop()
            ln -= 1
            
        if self.buf and len != -1:
            self.buf[ln] = self.buf[ln].rstrip()
    
    def insert_code(self, code):
        """Inserts a line of text after the last 'new_line' token. 
        
        Returns False if there is no line token in this buffer; True otherwise.
        """
        p = self._get_insert_point()
        if p[0] is not self:
            return False
        
        self.buf.insert(p[1], "\n" + "\t".expandtabs(p[2]*4))
        self.buf.insert(p[1], code)
        return True
                  
    def _get_ins_name(self, ofs):
        # Returns the buffer insert position as a string
        p = self.pb
        cnt = 0
        while p:
            cnt += len(p.buf)
            p = p.pb
        
        return str(cnt+ofs)    
    
    def _get_insert_point(self):
        # Returns a tuple for (insert buffer, insert index, tab count, position name)
        if self.inobject:
            return self.pb._get_insert_point()
        
        cnt = len(self.buf)-1
        
        while cnt != -1:
            if self.buf[cnt].startswith("\n") and self.buf[cnt].isspace():
                return (self, 
                        cnt+1,
                        int(self.buf[cnt].count(" ")/4), 
                        self._get_ins_name(cnt))
            cnt -= 1
            
        return self.pb and self.pb._get_insert_point() or (self, 0, 0, "0")  
    
    def insert_prefix(self, token, altmap={}):
        """Inserts a prefix string into the buffer before the current CodeEntry.
        
        This method contains heuristics to determine if the current entry is part of a hierarchical 
        path (i.e. "part.info"). In such case, the 'token' argument is placed before the path. 
        'altmap' is used to supply alternate namespace mappings such as {'this': 'self'} (optional).        
        """
        offs = len(self.buf)
        e = self.current()
        
        while e.is_nested() and offs > -1:
            offs -= 1
            e = e.par
            if isinstance(e, End): # give up if extends a function or expression (not a variable)
                return False
            
            nm = e.name or str(e)
            
            # search backward through string buffer to begin    
            while offs > -1:
                if self.buf[offs] == altmap.get(nm, nm):
                    break
                offs -= 1
        
        if offs != -1:
            self.buf.insert(offs, token)
            return True
                    
        return False
    
    
    def insert_function(self, code):
        """Inserts a js function into the buffer and returns the function name.
        
        The function code should not have a name or type prefix and must by written in javascript.
        """
        ins = self._get_insert_point()
        fname = "_func_"+ins[3]
        e = CodeFactory("function "+fname+code, self.rules._keywords).get_code()
        cb = CodeBuffer(e, self.rules)
        cb.pb = self
        cb.inset = ins[2]
        # cb.new_line()
        cb.transpile()
        cb.trim()
        cb.new_line()
        b = ins[0].buf
        cnt = ins[1]
        ins[0].buf = cnt and b[:cnt] + cb.buf + b[cnt-1:] or cb.buf + b
                        
        return fname
    

    
    def insert_import_statement(self, code):
        """Inserts a javascript import statement and registers its attributes."""
        
        while self.pb:
            self = self.pb
        
        # insure statement is closed    
        if not code.rstrip().endswith(";"):
            code += ";"
            
        ea = CodeFactory(code, self.rules._keywords).get_code().entries()
        sb = self.get_slice(0, 0)
        sb.inset = 0
        sb.entries.extend(ea)
        sb.size = len(ea)
        
        if self.import_map._register_import(ea[0], sb):
            sb.new_line()
            sb.transpile()
            sb.trim()
            
            b = self.buf
            ln = len(b)
            pos = self.head_offs
            
            while pos < ln and b[pos].find("\n") == -1:
                pos += 1
            
            if pos == ln:
                sb.new_line()
                     
            self.buf = b[:pos] + sb.buf + b[pos:]
            self.head_offs = pos + len(sb.buf)
            return True
                
        return False
      
    def mark_header_offset(self):
        """Marks the next insert position for header code."""
        # Note: This function should only be called by CodeRules that handle 'KW_import' or other header entries
        
        self.head_offs = len(self.buf)-1        
        
           

class HeadingBuffer():
    """Used to insert code at near the top of a function or class.
    
    The buffer uses a key map to prevent double entry. The map and insert
    position are reset between transpiling of top level functions or class
    methods. Instances of HeadingBuffer are accessed by the 'heading' attribute
    of CodeBuffer.
    """
    
    def __init__(self, buffer):
        self.cb = buffer
        self.pos = 0
        self.reg = {}
        self.newline = "\n"
        
    def mark(self):
        """Resets the buffer map and insert position."""
        
        self.reg = {}
        self.pos = len(self.cb.buf)
        self.newline = "\n" + self.cb.indent()
      
    def insert(self, key, code):
        """Conditionally inserts code identified by a unique key."""
         
        if self.reg.get(key):
            return False
        
        self.reg.update({key: self.pos})
        self.cb.buf.insert(self.pos, code)
        self.cb.buf.insert(self.pos+1, self.newline)
        self.pos+=2
        return True
    
    
class ImportMap():
    """Maintains a registry of imported variables.
    
    Instances of ImportMap are accessed by the 'import_map' attribute of
    CodeBuffer.
    """
    def __init__(self):
        self.varset = set()
        self.sourceFiles = {}
        
    def is_imported(self, name):
        """Returns True if the specified name is an imported variable."""
        
        return name in self.varset
    
    def get_imported_as(self, name, file):
        """Returns the alias or 'as' import name for the specified name and file."""
         
        sf = self.sourceFiles.get(file)
        return sf and sf.get(name) or None
        
    def _register_import(self, impStm, buffer):
        if not isinstance(impStm, KW_import):
            return False
        
        sb = buffer.get_sub_buffer(impStm)
        vm = {}
        sf = None
        
        for e in sb.entries:
            if e.name == "from":
                sf = self._get_source_file(e.get_next().value_of())
                
            elif isinstance(e, Attribute):
                vm.update({e.value: e.value})
                    
            elif isinstance(e, StringType):
                sf = self._get_source_file(e.value_of())
                
        if sf != None:
            sf.update(vm)
            
        self.varset.update(vm.values())            
        return True
                
    def _get_source_file(self, src):
        sf = self.sourceFiles.get(src)
        if sf == None:
            sf = {}
            self.sourceFiles.update({src: sf})
            
        return sf            
    
                    
class CodeRule():
    """An abstract rule for interpreting a sequence of one or more CodeEntry nodes."""
    
    def __init__(self, name="default_rule", path=None):
        self.name = name
        self.rulePath = path and path or []
        
    def path(self):
        """Iteration of class names requires to match this rule."""
        
        return iter(self.rulePath)
    
    def apply(self, buffer, offset):
        """Evaluates CodeBuffer state and translates the result.
        
        This method is called after a RuleManager has determined that the rule MAY
        apply to the current CodeBuffer state. The method will typically respond
        by checking the current CodeEntry pointed to by the buffer and, in many
        cases, evaluating the entry attributes and the attributes of nearby
        entries.
        
        If a determination is made that the rule does apply, the CodeRule
        instance may append and/or insert translated code. Afterward, it returns
        the total number of CodeEntries that were evaluated. If no entries are
        evaluated, the method returns 0. The CodeBuffer's pointer will be
        advanced by the number returned.
        
        buffer = the CodeBuffer being evaluated
        offset = the index offset of the last matching entry of the rules signature. 
            Calling buffer.current(offset) returns the last entry.
        """
        return 1


class BasicRule(CodeRule):
    """Implementation of CodeRule that matches all CodeEntry instances with the
    specified class name.
    
    When matched with a CodeBuffer state, the rule appends the matched entry's
    'str' value followed by an optional token.
    """
    
    def __init__(self, name, token=""):
        super().__init__(name, [name]) 
        self.token = token
        
    def apply(self, buffer, offset):
        buffer.add(str(buffer.current()))
        buffer.add(self.token)    
        return 1

class DefaultRule(CodeRule):
    """Applies the BasicRule to a list of CodeEntry class names."""
    
    def __init__(self, name, rulelist=[], token=""):
        super().__init__(name, rulelist.copy()) 
        self.token = token
        
    def path(self):
        return []
    
    def apply(self, buffer, offset):
        c = buffer.current()
        if type(c).__name__ in self.rulePath:
            buffer.add(str(c))
            buffer.add(self.token)    
            return 1 
        
        return 0

    
def to_dom_file(filein, fileout=None):
    """Translates a source .js file to human readable Document Object Model file.
    
    If 'fileout' is not specified, the default is the same as the input file
    with a '.dom' suffix.
    """
    filein = Path().absolute().joinpath(filein).resolve()
            
    if not fileout:
        fileout = filein.with_suffix(".dom") 
      
    with open(str(filein), "r") as f:
        data = f.read()
        
    src = to_dom_string(data)
            
    with open(str(fileout), "w") as f:
        f.write(src) 


def to_dom_string(text):
    """Translates javascript source code into human readable Document Object Model string."""
    
    cf = CodeFactory(text, Keywords().get_code_instance)
    code = cf.get_code()
    buf = []
    
    try:
        for ent in code.entries():
            buf.append(_default_string(ent)+"\n")
    finally:  
        pass  
    
    return "".join(buf)


def format_code(sourcecode, rules="jsconvert.pyrules"):
    """Returns a translated version of the input javascript source code string.
    
    The optional 'rules' argument may be a RuleManager instance or the name of a rules module. 
    If not specified, the default rules will convert to Python.    
    """
        
    rm = rules if isinstance(rules, RuleManager) else RuleManager(str(rules))
    return "".join(CodeBuffer(sourcecode, rm).transpile())


def convert(filein, fileout=None, rules="jsconvert.pyrules", dom=False):
    """Translates javascript source code in a directory or file using 
    the optional rules module.
    
    This method will also recurse sub-directories. If a rules module is not
    specified, the default rules will convert to Python. If 'fileout' is not
    specified, the default is 'filein' resolved with the output suffix.
    """

    filein = Path().absolute().joinpath(filein).resolve()
    if not filein.exists():
        raise IOError("Input File:'"+str(filein)+"' does not exist.")
    
    ext = _get_ext(rules)
    outx = ext.get("output")
    isdir = filein.is_dir()
    
    if not fileout:
        fileout = (isdir and filein) or filein.with_suffix(outx)
        
    else:
        fileout = Path().absolute().joinpath(fileout).resolve()
        if isdir and not fileout.is_dir():
            fileout = fileout.parent
            
    if not (fileout if fileout.is_dir() else fileout.parent).exists():
        raise IOError("Output File:'"+str(filein)+"' does not exist.")
        
    files = _loadFiles(filein, ext.get("input"))
    if not filein.is_dir():
        filein = filein.parent
    
    
    for f in files:
        if fileout.is_dir():
            rel = f.relative_to(filein)
            fo = fileout.joinpath(rel).resolve().with_suffix(outx)
        else:
            fo = fileout
        
        if f == fo:
            raise Exception("Can't output to input file")
        
        try:
            if not fo.parent.exists():
                fo.parent.mkdir(parents=True, exist_ok=True)
                
            if fo.exists():
                with open(str(fo), "r") as fin:
                    try:
                        while True:
                            line = fin.readline().strip()
                            if not line.startswith("#"):
                                break
                            if "no-edit" in line[1:].split(" "):
                                raise NoEditException()
                            
                    except EOFError:
                        pass
                    
            print("importing: "+str(f)) 
            with open(str(f), "r") as fin:
                data = fin.read()
                    
            if dom:
                print("compiling...")
                ds = to_dom_string(data)
                    
                with open(str(fo.with_suffix(ext.get("dom"))), "w") as rout:
                    rout.write(ds)
                    
                    
            print("exporting: "+str(fo))    
            src = format_code(data, rules)
                
            with open(str(fo), "w") as fout:
                fout.write(src)
                 
            print("export complete: ")
        except NoEditException:
            print("editing not allowed: "+str(fo))
            
        except RuleProcessingException as pe:
            pe.printStack()
               
        except Exception as err:
            print("error: "+str(f)+" Exception: "+ str(err))
    
    if isdir:
        fs = _loadDir(fileout, fileout.is_dir())
        print("updating "+str(len(fs))+" 'init' files...")
        
        for dr in fs:
            fa = []
            for f in dr.iterdir():
                if not f.is_dir() and f.suffix == outx and not f.name.startswith("_"):
                    fa.append('"'+f.stem+'",')
           
            ns = "__all__ = ["+"".join(fa).rstrip(",")+"]" if fa else ""
            txt = ns
            inif = dr.joinpath("__init__.py").resolve()
            
            if inif.exists():       
                with open(str(inif), "r") as fin:
                    txt = fin.read()
                    p1 = txt.find("__all__")
                    p2 = txt.find("]", p1+1)
                    if p1 != -1 and p2 != -1:
                        if p2 < len(txt)-1:
                            ns += txt[p2+1:]
                        txt = txt[:p1] + ns
                    else:
                        txt += "\n"+ns
            
            with open(str(inif), "w") as fout:
                fout.write(txt)              

    print("conversion complete")
       
    
def list_rules(ruleset, buf=None):
    """Utility that will recursively list all CodeRule sub-class within a module."""
    
    if buf is None:
        buf = []
        
    rm = import_module(ruleset, "jsconvert")
    # ignor = rm.IGNORE_RULES if hasattr(rm, "IGNORE_RULES") else []
    
    if hasattr(rm, "__path__"):
        for m in rm.__all__:
            if not m.startswith("_"): # filter out __init__ or special files
                list_rules(ruleset+"."+m, buf)
    else:
        for m in rm.__all__:
            r = getattr(rm, m)
            if callable(r):
                r = r()
                if isinstance(r, CodeRule):
                    buf.append(r)

    return buf                
                    
                
    
    