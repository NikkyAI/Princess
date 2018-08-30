import tatsu, princess, io, contextlib, logging, os, functools, inspect, sys, re

from princess import ast_repr, grammar
from princess.ast import node
from unittest import skip, skipIf, skipUnless, expectedFailure

import pytest

def prog(n): return node.Program([n])

class opt:
    TRACEBACK = True
    COLORIZE = False

def _traceback(src, **kwargs):
    if opt.COLORIZE and not "colorize" in kwargs:
        kwargs["colorize"] = True
    if opt.TRACEBACK and not ("trace" in kwargs and kwargs["trace"]):
        with io.StringIO() as buf:
            handlers = tatsu.util.logger.handlers
            tatsu.util.logger.handlers = [logging.StreamHandler(buf)]
            try:
                princess.parse(src, trace = True, **kwargs)
            except tatsu.exceptions.FailedParse: pass
            finally:
                tatsu.util.logger.handlers = handlers

            return buf.getvalue()
    return None

#class FailedParse(Exception):
#    def __init__(self, src, exception, trace = False, **kwargs):
#        self.trace = _traceback(src, **kwargs)
#        self.exception = exception
#
#    def __str__(self):
#        res = str(self.exception) if self.exception else ""
#        if self.trace: 
#            res += "\n\nParser Trace: \n" + self.trace
#        return res

def parse(text, **kwargs):
    if opt.COLORIZE and not "colorize" in kwargs:
        kwargs["colorize"] = True
        
    parsed = princess.parse(text, **kwargs)
    parsed._src = text
    return parsed

def _generate_traceback(arg):
    if not isinstance(arg, princess.ast.Node): return None
    if not hasattr(arg, "_src"): return None 
    return _traceback(arg._src)

#def _append_traceback(e, first, second, prepend = None):
#    if not opt.TRACEBACK: raise e
#
#    first = _generate_traceback(first)
#    second = _generate_traceback(second)
#    if first == None and second == None: raise e
#
#    sep = "\n"
#    
#    ret = prepend if prepend is not None else "\n\n"
#    if first == None: 
#        first = second
#        second = None
#    if second == None:
#        ret += "Parser Trace:" + sep
#    else:
#        ret += "Parser Trace 1:" + sep
#    #print("ret: ", ret)
#    #print("first: ", first)
#    #print("second: ", second)
#    ret += first
#    if second != None:
#        ret += sep + "Parser Trace 2:" + sep + second
#
#    return AssertionError(str(e) + ret)

#class OldTestCase(unittest.TestCase):
#    def assertEqual(self, first, second, msg = None):
#        e = None
#        try: return super().assertEqual(first, second, msg)
#        except AssertionError as ex: e = ex
#        if e: raise _append_traceback(e, first, second)
#
#    def assertNotEqual(self, first, second, msg = None):
#        e = None
#        try: return super().assertNotEqual(first, second, msg)
#        except AssertionError as ex: e = ex
#        if e: raise _append_traceback(e, first, second)


#    assertEquals = assertEqual
#    assertNotEquals = assertNotEqual

Integer = node.Integer
Float = node.Float
String = node.String
Boolean = node.Boolean

def Identifier(*args):
    return node.Identifier(list(args))
def Var(*args, **kwargs):
    return node.VarDecl(keyword = 'var', *args, **kwargs)
def Let(*args, **kwargs):
    return node.VarDecl(keyword = 'let', *args, **kwargs)

def assertFailedParse(code, regex = None): 
#    e = None
    parsed = None
#    try: 
#        if regex:
#            with self.assertRaisesRegex(tatsu.exceptions.FailedParse, regex): parsed = princess.parse(code)
#        else: 
#            with self.assertRaises(tatsu.exceptions.FailedParse): parsed = princess.parse(code)
#    except AssertionError as ex: e = ex
#    if e:
#        prepend = None
#        if parsed is None: parsed = princess.ast.Node()
#        else: prepend = "\n\nResult: " + ast_repr(parsed) + "\n\n"
#        parsed._src = code
#        raise _append_traceback(e, parsed, None, prepend = prepend)
    try:
        parsed = princess.parse(code)
        print(_generate_traceback, file=sys.stderr)
        raise AssertionError("No ParseException raised. Result = " + str(parsed))
    except tatsu.exceptions.FailedParse as ex:
        if regex and not re.search(regex, str(ex)):
            raise AssertionError("Exception message was `" + str(ex) + "` expected one matching the regex " + repr(regex))
