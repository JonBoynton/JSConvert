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

from pathlib import Path, WindowsPath
from importlib import import_module
from jsconvert.comp import  CodeFactory, Attribute, StringType, Container, Comment, EMPTY, Block
from jsconvert.lang import Keywords, KW_import

__author__ = "Jon L. Boynton"
__copyright__ = "Jon L. Boynton 2022"
__license__ = "Apache License, Version 2.0"

def _loadFiles(dir_, ext=".js", files=None):
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
    rm = import_module(ruleset)
    return {
        "input": hasattr(rm, "INPUT_FILE_EXTENSION") and rm.INPUT_FILE_EXTENSION or ".js",
        "output": hasattr(rm, "OUTPUT_FILE_EXTENSION") and rm.OUTPUT_FILE_EXTENSION or ".py",
        "dom": hasattr(rm, "DOM_FILE_EXTENSION") and rm.DOM_FILE_EXTENSION or ".dom",
        }
    
      

class RuleManager():
    """Maintains a collection of code rules for transcribing source files.
    
    This manager is constructed using the name of a module that contains
    CodeRule classes.  Classes and sub-modules are identified by the '__all__'
    property.  Classes not listed in '__all__' are ignored. The module will be
    recursively scanned for additional modules and packages.  In addition, an
    optional Keywords object can be provided to create alternate DOM schemes.
    """
    
    def __init__(self, module="", keywords=Keywords().get_code_instance):
        self.head = RuleBucket()
        self.head.keywords = keywords
        self.last_rule = CodeRule()
        if module:
            self.add_rules(module)
            
    def add_rules(self, moduleName):
        """Adds a module of CodeRule classes to this manager."""
        
        for r in list_rules(moduleName):
            self.add_rule(r)
        
    def add_rule(self, rule):
        """Adds a single CodeRule instance to this manager."""
        
        b = self.head
        for e in rule.path():
            b = b.add(e)
            
        b.list.append(rule)
        
    def transpile(self, code):
        """Returns a translated version of the input source code string."""
        
        return "".join(self._create_code_buffer(code).transpile())

    def _create_code_buffer(self, code):
        e = CodeFactory(code, self.head.keywords).get_code()
        return CodeBuffer(e, self.head)

        
class RuleBucket():
    """Provides a hierarchical directory for matching and processing code rules."""
    
    def __init__(self):  
        self.map = dict(())
        self.list = []
        
    def get(self, name):
        """Returns a RuleBucket for the specified name or None if not found"""
        return self.map.get(name)
            
    def add(self, name):
        """Adds a new RuleBucket with the specified name.
        
        Returns the new bucket if created or the old bucket if it already
        existed.
        """
        e = self.map.get(name)
        if not e:
            e = name != "ANY" and RuleBucket() or AnyBucket()
            self.map.update({name: e})
            
        return e

    def process(self, buffer, offs=0):
        """Evaluates the CodeEntry at the current buffer position + offs."""
        
        pos = buffer.offset + offs
        if pos < buffer.size:
            b = self.map.get(type(buffer.entries[pos]).__name__)
            
            if b and b.process(buffer, offs+1):
                return True
            
            b = self.map.get("ANY")
            
            if b and b.process(buffer, offs+1):
                return True
            
        for itm in self.list:
            i = itm.apply(buffer, offs-1)
            if i:
                buffer.offset += i
                return True
        
        # advance to next entry if not handled by any Rule   
        if self is buffer.bucket:
            buffer.offset += 1
            return True
           
        return False
        

class AnyBucket(RuleBucket):
    """Variation of RuleBucket for evaluating all child components of a buffer entry."""
    
    def process(self, buffer, offs=0):
        offs -= 2
        c = buffer.current(offs)
        for c in c.get_children():
            while buffer.entries[buffer.offset + offs] is not c:
                offs += 1
                
            if super().process(buffer, offs):
                return True
            offs += 1
                      
        return False

    
class NoEditException(Exception):
    """Raised during transpiling to prevent overwriting a working document."""
    
    def __init__(self, msg="No-Edit"):
        super().__init__(msg)

            
class CodeBuffer():
    """CodeBuffer provides a list for accumulating translated strings.
    
    It also maintains a linear index of DOM components.  The buffer is
    responsible for advancing the index pointer as transpiling progresses.  In
    addition, it provides various methods for evaluating and manipulating the
    DOM.
    """
    def __init__(self, rootEntry, bucket):
        rootEntry._pack()
        self.buf = []
        self.offset = 0
        self.entries = []
        self.bucket = bucket
        self.heading = None
        self.import_map = None
        self.pb = None # parent buffer (if any)
        self.par_offs = 0
        self.head_offs = 0 # header insert position
        self.inobject = False # if buffer is inside an object type
        self.inset = 0
        importing = False
        # self.comments = comments # preserve comments in code
        
        if isinstance(rootEntry, Container):
            self.heading = HeadingBuffer(self)
            self.import_map = ImportMap()
            
            if (rootEntry.stack and 
                isinstance(rootEntry.stack[0], Comment) and 
                rootEntry.stack[0].noEdit()):
                raise NoEditException()
                
            for e in rootEntry.entries():
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
        
    #    try:
        while self.offset < self.size:
            self.bucket.process(self)
    #    except Exception as err:
    #        print("trap Exception: "+ str(err))
      
        return self.buf
    
    def get_slice(self, bgn, end):
        """creates an new instance of this buffer with a slice of indexed components."""
        
        cb = CodeBuffer(EMPTY, self.bucket)
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
        """Adds a buffer to the end of this buffer and returns the number of components added ."""
        
        if not cb.entries:
            return 0
        
        # PYTHON BUG: self.buf.extend(cb.convert()) did not extend first time through
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
    
    def indent(self):
        """Returns a string of space characters representing the current tab inset."""
        
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
        """Appends a single space character to the buffer."""
        
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
        """Inserts a line of code after the last 'new_line' token. 
        
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
    
    def insert_function(self, code):
        """Inserts a function into the buffer and returns the function name.
        
        The function code should not have a name or type prefix.
        """
        ins = self._get_insert_point()
        fname = "_func_"+ins[3]
        e = CodeFactory("function "+fname+code, self.bucket.keywords).get_code()
        cb = CodeBuffer(e, self.bucket)
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
            
        ea = CodeFactory(code, self.bucket.keywords).get_code().entries()
        sb = self.get_slice(0, 0)
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
    
    if isinstance(Path().absolute(), WindowsPath):
        filein =  Path(filein.replace("/", "\\"))
        if fileout:
            fileout = Path(str(Path().absolute())+fileout.replace("/", "\\")).resolve()  
            
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

    
def to_src_string(text, rules="jsconvert.pyrules"):    
    """Translates javascript source code using the optional rules module.
    
    If a rules module is not specified, the default rules will convert to
    Python.
    """
    
    try:
        rm = RuleManager(rules)
        return rm.transpile(text)
    
    finally:  
        pass  
    
    return "failed"


def convert(filein, fileout=None, rules="jsconvert.pyrules", dom=False):
    """Translates javascript source code in a directory or file using 
    the optional rules module.
    
    This method will also recurse sub-directories. If a rules module is not
    specified, the default rules will convert to Python. If 'fileout' is not
    specified, the default is 'filein' resolved with the output suffix.
    """

    filein = Path().absolute().joinpath(filein).resolve()
    ext = _get_ext(rules)
    
    if not fileout:
        fileout = (filein.is_dir() and filein) or filein.with_suffix(ext.get("output"))
    else:
        fileout = Path().absolute().joinpath(fileout).resolve()
        
    files = _loadFiles(filein, ext.get("input"))
    if not filein.is_dir():
        filein = filein.parent
        
    for f in files:
        if fileout.is_dir():
            rel = f.relative_to(filein)
            fo = fileout.joinpath(rel).resolve().with_suffix(ext.get("output"))
        else:
            fo = fileout
        
        if f == fo:
            raise Exception("Can't output to input file")
        
        try:
            if not fo.parent.exists():
                fo.parent.mkdir(parents=True, exist_ok=True)
                
            print("importing: "+str(f)) 
            with open(str(f), "r") as fin:
                data = fin.read()

            if dom:
                print("compiling...")
                ds = to_dom_string(data)
                    
                with open(str(fo.with_suffix(ext.get("dom"))), "w") as rout:
                    rout.write(ds)
                    
            print("exporting: "+str(fo))    
            src = to_src_string(data, rules)
                
            with open(str(fo), "w") as fout:
                fout.write(src)
                 
            print("export complete: ")
        except NoEditException:
            print("export not allowed: "+str(fo))
               
        except Exception as err:
            print("error: "+str(f)+" Exception: "+ str(err))
        
    
def list_rules(ruleset, buf=None):
    """Utility that will recursively list all CodeRule sub-class within a module."""
    
    if buf is None:
        buf = []
    rm = import_module(ruleset)
    if hasattr(rm, "__path__"):
        for m in rm.__all__:
            if not m.startswith("_"):
                list_rules(ruleset+"."+m, buf)
    else:
        for m in rm.__all__:
            r = getattr(rm, m)
            if callable(r):
                r = r()
                if isinstance(r, CodeRule):
                    buf.append(r)

    return buf                
                    
                
    
    
