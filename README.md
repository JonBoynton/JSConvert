# JSConvert
A utility for transpiling Javascript(ES6) source code to Python and other languages.
<br>
<br>
<br>
# Overview
JSConvert provides a framework for transpiling Javascript (ES6) source code to Python and other programming languages.  The framework is written 100% in Python 3 and can be easily extended using “Code Rule” objects. Rule modules make it easy to test and modify existing rules or create new ones.  Reference modules for transpiling to Python and Javascript are included. 

# Why use JSConvert?

If you need to release your source code in another language, you need a Transpiler. The goal of JSConvert is to preserve as much of the authors original design intent as possible while producing a runnable (or nearly runnable) result. No need to re-write your whole project. Transpiled source code is easier to cross reference, debug, maintain, and optimize.

A good Transpiler must do more than simply convert syntax. This is why JSConvert was developed with a rules engine that can grow and be refined as needed.  Rules can be used to refactor, add poly-fills, fix code, and more. In theory, given a correct set of rules, JSConvert can transpile Javascript to almost any comparable language.


# How to use

To convert Javascript to Python, use one of two functions in the transpilier module: convert() or to_src_string(). The convert() function accepts a path argument to a ".js" file or to a directory containing ".js" files. The to_src_string() function, as the name implies, will directly transpile JS to Python and output the result as a string.

**Example 1:**

```py
import jsconvert.transpiler as trans

trans.convert("C:/myUserPath/some_file.js")
```

By default, a transpilied output *.py file with the same name and directory as the input *.js file(s) will be created. If a directory path is specified, the convert function will traverse all sub-directories and include every *.js  file.

*Optional* convert() keyword arguments:
- fileout = the output file path, 
- rules = name of a rule module used for transpiling. Default is "jsconvert.pyrules"
- dom = True|False. Create a .dom text file for each javascript file. Used for debugging and making rules. Default is False

**Example 2:**

```py
import jsconvert.transpiler as trans

print(trans.to_src_string("var someJSvar = 'some value';"))
```

*Optional* to_src_string () keyword argument:
- rules = name of rule module used for transpiling. Default is "jsconvert.pyrules"

# How to extend
JSConvert currently includes two reference modules: “jsconvert.jsrules” and “jsconvert.pyrules”. As their names imply, jsrules are used to convert JS to JS while pyrules convert JS to Python3. A rule module can be specified by the “rules” keyword argument passed into either the convert() or to_src_string() functions as described above. 

Each rule module contains a set of classes that extend “jsconvert.transpiler.CodeRule”. Developers that wish to modify source output can do so by modifying rule classes, adding rules, or changing rule precedence. In addition, developers can create their own rule modules to transpile JS to other languages or versions. For details and examples, see API documentation.

# What's next?

Here are some key areas that need further development:

1. A simple user interface<br>
Having a UI to select and preview files would be a nice addition.<br><br>

2. Library support<br>
Automatically transpiling imported library source code is currently not supported. JSConvert does evaluate the import code but it does not transpile the libraries themselves.<br><br>

3. Typed variables<br>
Introspection of variables to determine primitive type is not supported.<br><br>

4. Improved language support<br>
The default behavior of JSConvert when transpiling is to pass-through code features it does not support. This means that they will be included in the output file but may look more like their original source than the target source.<br><br>

Some features in the pyrules module that still need poly-fills include:

1. “for” loops<br>
Python “for” loops use an iterator and range model that does not easily translate from javascript.<br><br>

2. “do while” loops<br>
There does not seem to be a pythonic analog to “do”<br><br>

3. Promises<br>
Lambda functions are supported in pyrules but the Promise Object might be handled better by using Python’s ‘async’ and ‘await’ features.<br><br>

4. byte[] arrays in JS<br>
  Could be handled directly in python where identified by a rule.<br><br>

**Conclusion:**<br>
> This is by no means an exhaustive list. However, it's a start. Thank you for your interest in this project. I sincerely hope that it is useful to you.<br><br><br>

# License
This project is licensed under the terms of [Apache License Version 2.0](https://www.apache.org/licenses/LICENSE-2.0)
<br>

