#!/usr/bin/python3.9

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from struct import pack
import subprocess, json, sys
from typing import List
import tatsu
from tatsu.walkers import NodeWalker
from pathlib import Path

GRAMMAR = r"""
    function_decl = ret: type_1 '(' args: ','.{ type_1 | varargs } ')';

    sign = 'signed' | 'unsigned';
    modifier = 'long' 'long' @:`'llong'` | 'long' | 'short';
    specifier = 'int' | 'char' | 'float' | 'double' | '__int128' | '_Bool';
    winptr = '__ptr32' | '__sptr' | '__uptr';

    identifier::Identifier      = /(?!\d)\w+/;
    tagged_idenitifier::Tagged  = ('struct' | 'union' | 'enum') identifier;
    primitive::Primitive        = [sign] [modifier] specifier | [sign] modifier | sign;
    pointer::Pointer            = type: type '*' {winptr | 'const' | 'volatile' | 'restrict'};
    array::Array                = type: type '[' size: [/\d+/] ']';
    function::Function          = ret: type / \(\*\)/ '(' args: ','.{ type_1 | varargs } ')';

    void::Void = 'void';
    varargs::Varargs = '...';

    type = pointer | function | array | void | primitive | tagged_idenitifier | identifier;
    type_1 = {winptr | 'const' | 'volatile' | '__unaligned'} @:type;
"""

PARSER = tatsu.compile(GRAMMAR, asmodel = True)

def parse(s):
    return PARSER.parse(s, start = "type_1")

class File:
    def __init__(self, fp) -> None:
        self.GLOBALS = {}
        self.TYPEDEFS = {}
        self.TAGGED = {}
        self.STRUCT_IDS = {}

        self.TAGGED["__va_list_tag"] = VaList()
        self.TYPEDEFS["bool"] = PRIMITIVES["_Bool"]
        if sys.platform == "darwin":
            self.TYPEDEFS["__SVInt8_t"] = PRIMITIVES["char"]
            self.TYPEDEFS["__SVInt16_t"] = PRIMITIVES["short"]
            self.TYPEDEFS["__SVInt32_t"] = PRIMITIVES["int"]
            self.TYPEDEFS["__SVInt64_t"] = PRIMITIVES["long"]
            self.TYPEDEFS["__SVUint8_t"] = PRIMITIVES["char"]
            self.TYPEDEFS["__SVUint16_t"] = PRIMITIVES["short"]
            self.TYPEDEFS["__SVUint32_t"] = PRIMITIVES["int"]
            self.TYPEDEFS["__SVUint64_t"] = PRIMITIVES["long"]
            self.TYPEDEFS["__SVFloat16_t"] = Integer("__SVFloat16_t") # short float ??
            self.TYPEDEFS["__SVFloat32_t"] = Integer("__SVFloat32_t")
            self.TYPEDEFS["__SVFloat64_t"] = Integer("__SVFloat64_t")
            self.TYPEDEFS["__SVBFloat16_t"] = Integer("__SVBFloat16_t")
            self.TYPEDEFS["__SVBFloat32_t"] = Integer("__SVBFloat32_t")
            self.TYPEDEFS["__SVBFloat64_t"] = Integer("__SVBFloat64_t")
            self.TYPEDEFS["__clang_svint8x2_t"] = Integer("__clang_svint8x2_t")
            self.TYPEDEFS["__clang_svint16x2_t"] = Integer("__clang_svint16x2_t")
            self.TYPEDEFS["__clang_svint32x2_t"] = Integer("__clang_svint32x2_t")
            self.TYPEDEFS["__clang_svint64x2_t"] = Integer("__clang_svint64x2_t")
            self.TYPEDEFS["__clang_svuint8x2_t"] = Integer("__clang_svuint8x2_t")
            self.TYPEDEFS["__clang_svuint16x2_t"] = Integer("__clang_svuint16x2_t")
            self.TYPEDEFS["__clang_svuint32x2_t"] = Integer("__clang_svuint32x2_t")
            self.TYPEDEFS["__clang_svuint64x2_t"] = Integer("__clang_svuint64x2_t")
            self.TYPEDEFS["__clang_svfloat16x2_t"] = Integer("__clang_svfloat16x2_t")
            self.TYPEDEFS["__clang_svfloat32x2_t"] = Integer("__clang_svfloat32x2_t")
            self.TYPEDEFS["__clang_svfloat64x2_t"] = Integer("__clang_svfloat64x2_t")
            self.TYPEDEFS["__clang_svbfloat16x2_t"] = Integer("__clang_svbfloat16x2_t")
            self.TYPEDEFS["__clang_svbfloat32x2_t"] = Integer("__clang_svbfloat32x2_t")
            self.TYPEDEFS["__clang_svbfloat64x2_t"] = Integer("__clang_svbfloat64x2_t")
            self.TYPEDEFS["__clang_svint8x3_t"] = Integer("__clang_svint8x3_t")
            self.TYPEDEFS["__clang_svint16x3_t"] = Integer("__clang_svint16x3_t")
            self.TYPEDEFS["__clang_svint32x3_t"] = Integer("__clang_svint32x3_t")
            self.TYPEDEFS["__clang_svint64x3_t"] = Integer("__clang_svint64x3_t")
            self.TYPEDEFS["__clang_svuint8x3_t"] = Integer("__clang_svuint8x3_t")
            self.TYPEDEFS["__clang_svuint16x3_t"] = Integer("__clang_svuint16x3_t")
            self.TYPEDEFS["__clang_svuint32x3_t"] = Integer("__clang_svuint32x3_t")
            self.TYPEDEFS["__clang_svuint64x3_t"] = Integer("__clang_svuint64x3_t")
            self.TYPEDEFS["__clang_svfloat16x3_t"] = Integer("__clang_svfloat16x3_t")
            self.TYPEDEFS["__clang_svfloat32x3_t"] = Integer("__clang_svfloat32x3_t")
            self.TYPEDEFS["__clang_svfloat64x3_t"] = Integer("__clang_svfloat64x3_t")
            self.TYPEDEFS["__clang_svbfloat16x3_t"] = Integer("__clang_svbfloat16x3_t")
            self.TYPEDEFS["__clang_svbfloat32x3_t"] = Integer("__clang_svbfloat32x3_t")
            self.TYPEDEFS["__clang_svbfloat64x3_t"] = Integer("__clang_svbfloat64x3_t")
            self.TYPEDEFS["__clang_svint8x4_t"] = Integer("__clang_svint8x4_t")
            self.TYPEDEFS["__clang_svint16x4_t"] = Integer("__clang_svint16x4_t")
            self.TYPEDEFS["__clang_svint32x4_t"] = Integer("__clang_svint32x4_t")
            self.TYPEDEFS["__clang_svint64x4_t"] = Integer("__clang_svint64x4_t")
            self.TYPEDEFS["__clang_svuint8x4_t"] = Integer("__clang_svuint8x4_t")
            self.TYPEDEFS["__clang_svuint16x4_t"] = Integer("__clang_svuint16x4_t")
            self.TYPEDEFS["__clang_svuint32x4_t"] = Integer("__clang_svuint32x4_t")
            self.TYPEDEFS["__clang_svuint64x4_t"] = Integer("__clang_svuint64x4_t")
            self.TYPEDEFS["__clang_svfloat16x4_t"] = Integer("__clang_svfloat16x4_t")
            self.TYPEDEFS["__clang_svfloat32x4_t"] = Integer("__clang_svfloat32x4_t")
            self.TYPEDEFS["__clang_svfloat64x4_t"] = Integer("__clang_svfloat64x4_t")
            self.TYPEDEFS["__clang_svbfloat16x4_t"] = Integer("__clang_svbfloat16x4_t")
            self.TYPEDEFS["__clang_svbfloat32x4_t"] = Integer("__clang_svbfloat32x4_t")
            self.TYPEDEFS["__clang_svbfloat64x4_t"] = Integer("__clang_svbfloat64x4_t")
            self.TYPEDEFS["__SVBool_t"] = PRIMITIVES["_Bool"]

        self.has_printed = set()
        self.fp = fp
        self.last_record = None

def escape_name(name: str) -> str:
    if name == "type":
        return "type_"
    elif name == "in":
        return "in_"
    elif name == "from":
        return "from_"
    return name
    
# Types

class Type:
    def __init__(self) -> None:
        self.qualname = None

    @abstractmethod
    def to_string(self, file: File) -> str:
        pass

    def to_definition(self, file: File) -> str:
        return self.to_string(file)
    
    def print_references(self, file: File):
        pass

class Void(Type):
    def to_string(self, file: File) -> str:
        return "void"
void = Void()

class Varargs(Type):
    def to_string(self, file: File) -> str:
        return "..."
varargs = Varargs()

class VaList(Type):
    def to_string(self, file: File) -> str:
        return "__va_list_tag"

class IncompleteType(Type):
    def __init__(self, name: str):
        self.name = name

    def to_string(self, file: File) -> str:
        return file.TAGGED[self.name].to_string(file)
    
    def to_definition(self, file: File) -> str:
        return file.TAGGED[self.name].to_definition(file)

class Float(Type):
    def __init__(self, name):
        self.name = name

    def to_string(self, file: File) -> str:
        return self.name
        
class Integer(Type):
    def __init__(self, name):
        self.name = name

    def to_string(self, file: File) -> str:
        return self.name

class Function(Type):
    def __init__(self, args: List[Type], ret: Type):
        self.args = args
        self.ret = ret

    def to_string(self, file: File) -> str:
        args = ', '.join(map(lambda x: x.to_string(file), filter(lambda x: x != void, self.args)))
        return f"def ({args}) -> ({self.ret.to_string(file) if self.ret != void else ''})"

class Pointer(Type):
    def __init__(self, tpe: Type):
        self.type = tpe

    def to_string(self, file: File) -> str:
        if self.type == void:
            return "*"
        else: return f"*{self.type.to_string(file)}"


class Array(Type):
    def __init__(self, tpe: Type, length = None):
        self.type = tpe
        self.length = length

    def to_string(self, file: File) -> str:
        if self.length:
            return f"[{self.length}; {self.type.to_string(file)}]"
        else:
            return f"*{self.type.to_string(file)}"

@dataclass
class Field:
    type: Type
    name: str
    is_bitfield: bool
    bit_size: int

    def to_definition(self, file: File) -> str:
        res = ""
        if self.is_bitfield:
            res += f"#bits({self.bit_size}) "
        res += f"{escape_name(self.name)}: {self.type.to_string(file)}"
        return res

class Record(Type):
    def __init__(self) -> None:
        self.typename = None
        self.fields: List[Field] = []
        self.name = None

    def to_string(self, file: File) -> str:
        if self.qualname:
            self = file.TAGGED[self.qualname]

        name = self.typename or self.name
        if not name: return self.to_definition(file)
        else: return name

    def print_references(self, file: File):
        if self.typename:
            self = file.TYPEDEFS[self.typename]
        elif self.qualname:
            self = file.TAGGED[self.qualname]
        
        if not self in file.has_printed:
            file.has_printed.add(self)
        else: return

        for f in self.fields:
            f.type.print_references(file)

        name = self.typename or self.name
        if name:
            print(f"export type {name}", file = file.fp, end = "")
            if self.fields:
                print(f" = {self.to_definition(file)}", file = file.fp)
            else: print("", file = file.fp)

class Struct(Record):
    def __init__(self, name: str, fields):
        self.name = ("s_" + name) if name else None
        self.fields = fields
        self.qualname = name
        self.typename = None

    def to_definition(self, file: File) -> str:
        if self.fields:
            res = "struct { "
            for field in self.fields:
                res += field.to_definition(file) + "; "
            res += "}"
            return res

class Union(Record):
    def __init__(self, name: str, fields):
        self.name = ("u_" + name) if name else None
        self.fields = fields
        self.qualname = name
        self.typename = None
    
    def to_definition(self, file: File) -> str:
        if self.fields:
            res = "struct #union { "
            for field in self.fields:
                res += field.to_definition(file) + "; "
            res += "}"
            return res

class Enum(Type):
    def __init__(self, name: str, fields):
        self.name = ("e_" + name) if name else None
        self.typename = None
        self.qualname = name
        self.fields = fields
    
    def to_string(self, file: File) -> str:
        if self.qualname:
            self = file.TAGGED[self.qualname]

        name = self.typename or self.name
        if not name: return self.to_definition(file)
        else: return name

    def to_definition(self, file: File) -> str:
        res =  "enum { "
        for (name, value) in self.fields:
            res += name
            if value:
                res += " = "
                res += value
            res += "; "
        res += "}"
        return res

    def print_references(self, file: File):
        if self.typename:
            self = file.TYPEDEFS[self.typename]
        elif self.qualname:
            self = file.TAGGED[self.qualname]
        
        if not self in file.has_printed:
            file.has_printed.add(self)
        else: return

        name = self.typename or self.name
        if name:
            print(f"export type {name}", file = file.fp, end = "")
            if self.fields:
                print(f" = {self.to_definition(file)}", file = file.fp)
            else: print("", file = file.fp)
        

#Global entities

class Declaration(ABC):
    @abstractmethod
    def to_declaration(self, n: int, file: File) -> str:
        pass

    @abstractmethod
    def to_symbol(self, n: int, file: File) -> str:
        pass

class ConstDecl(Declaration):
    def __init__(self, name: str, type: Type, value: str) -> None:
        self.name = name
        self.type = type
        self.value = value

    def to_declaration(self, file: File) -> str:
        return f"export const {self.name}: {self.type.to_string(file)} = {self.value}"
    
    def to_symbol(self, n: int, file: File) -> str:
        return ""

class VarDecl(Declaration):
    def __init__(self, name: str, type: Type, dllimport: bool):
        self.name = name
        self.type = type
        self.dllimport = dllimport

    def to_declaration(self, file: File) -> str:
        ret = "export import var #extern "
        if self.dllimport:
            ret += "#dllimport "

        ret += f"{self.name}: {self.type.to_string(file)}"
        return ret

    def to_symbol(self, n: int, file: File) -> str:
        variable = ""
        if not self.dllimport:
            variable = f", variable = *{self.name} !*"

        ret = f"__SYMBOLS[{n}] = {{ kind = symbol::SymbolKind::VARIABLE, dllimport = {'true' if self.dllimport else 'false'}, name = \"{self.name}\"{variable}}} !symbol::Symbol"
        return ret

class FunctionDecl(Declaration):
    def __init__(self, name: str, ret: Type, args, variadic: bool, dllimport: bool):
        self.name = name
        self.ret = ret
        self.args = args
        self.variadic = variadic
        self.dllimport = dllimport

    def to_declaration(self, file: File) -> str:
        args = []
        for (name, tpe) in self.args:
            args.append(name + ": " + tpe.to_string(file))
        if self.variadic:
            args.append("...")
        
        ret = "export import def #extern "
        if self.dllimport:
            ret += "#dllimport "

        ret += f"{self.name}({', '.join(args)})"
        if self.ret != void: ret += " -> " + self.ret.to_string(file)

        return ret

    def to_symbol(self, n: int, file: File) -> str:
        function = ""
        if not self.dllimport:
            function = f", function = *{self.name} !def () -> ()"

        ret = f"__SYMBOLS[{n}] = {{ kind = symbol::SymbolKind::FUNCTION, dllimport = {'true' if self.dllimport else 'false'}, name = \"{self.name}\"{function}}} !symbol::Symbol"
        return ret

PRIMITIVES = {
    ('char'): Integer("char"),
    ('signed', 'char'): Integer("char"),
    ('unsigned', 'char'): Integer("char"),
    ('short'): Integer("short"),
    ('short', 'int'): Integer("short"),
    ('signed', 'short'): Integer("short"),
    ('signed', 'short', 'int'): Integer("short"),
    ('unsigned', 'short'): Integer("ushort"),
    ('unsigned', 'short', 'int'): Integer("ushort"),
    ('int'): Integer("int"),
    ('signed'): Integer("int"),
    ('signed', 'int'): Integer("int"),
    ('unsigned',): Integer("uint"),
    ('unsigned', 'int'): Integer("uint"),
    ('long'): Integer("long"),
    ('long', 'int'): Integer("long"),
    ('signed', 'long'): Integer("long"),
    ('signed', 'long', 'int'): Integer("long"),
    ('unsigned', 'long'): Integer("ulong"),
    ('unsigned', 'long', 'int'): Integer("ulong"),
    ('llong'): Integer("int64"),
    ('llong', 'int'): Integer("int64"),
    ('signed', 'llong'): Integer("int64"),
    ('signed', 'llong', 'int'): Integer("int64"),
    ('unsigned', 'llong'): Integer("uint64"),
    ('unsigned', 'llong', 'int'): Integer("uint64"),
    ('__int128'): Integer("int128"),
    ('signed', '__int128'): Integer("int128"),
    ('unsigned', '__int128'): Integer("uint128"),
    ('float'): Float("float"),
    ('double'): Float("double"),
    ('long', 'double'): Float("float80"),
    ('_Bool'): Integer("uint8")
}

class Walker(NodeWalker):
    def __init__(self, file: File) -> None:
        super().__init__()
        self.file = file

    def walk_Primitive(self, node):
        return PRIMITIVES[node.ast]
    
    def walk_Void(self, node):
        return void
    
    def walk_Varargs(self, node):
        return varargs
    
    def walk_Pointer(self, node):
        return Pointer(self.walk(node.type))

    def walk_Array(self, node):
        return Array(self.walk(node.type), int(node.size) if node.size else None)

    def walk_Identifier(self, node):
        return self.file.TYPEDEFS[node.ast]

    def walk_Tagged(self, node):
        name = node.ast[1].ast
        if name in self.file.TAGGED:
            return self.file.TAGGED[name]
        else:
            return IncompleteType(name)
    
    def walk_Function(self, node):
        return Function(list(map(self.walk, node.args)), self.walk(node.ret))

def get_type(node) -> str:
    tpe = node["type"]
    if "desugaredQualType" in tpe:
        desugared = tpe["desugaredQualType"]
        if is_anonymous(desugared):
            return tpe["qualType"]
        return desugared
    else: return tpe["qualType"]

def walk_Expression(node):
    kind = node["kind"]
    if kind == "ConstantExpr":
        return walk_Expression(node["inner"][0])
    elif kind == "IntegerLiteral":
        return node["value"]
    elif kind == "UnaryOperator":
        opcode = node["opcode"]
        
        if opcode == "!": opcode = "not"

        return "(" + opcode + " " + walk_Expression(node["inner"][0]) + ")"
    elif kind == "BinaryOperator":
        opcode = node["opcode"]

        if opcode == "&&": opcode = "and"
        elif opcode == "||": opcode = "or"

        return ("(" + walk_Expression(node["inner"][0]) + " " + 
            opcode + " " + walk_Expression(node["inner"][1]) + ")")
    elif kind == "ParenExpr":
        return "(" + walk_Expression(node["inner"][0]) + ")"
    elif kind == "DeclRefExpr":
        return node["referencedDecl"]["name"]
    elif kind == "ConditionalOperator":
        return (walk_Expression(node["inner"][1]) + " if " +
            walk_Expression(node["inner"][0]) + " else " +
            walk_Expression(node["inner"][2]))
    return ""

def walk_VarDecl(node, file: File):
    name = node["name"]
    tpe = parse(get_type(node))
    tpe = Walker(file).walk(tpe)
    dllimport = False
    if "inner" in node:
        for param in node["inner"]:
            if param["kind"] == "DLLImportAttr":
                dllimport = True

    file.GLOBALS[name] = VarDecl(name, tpe, dllimport)

def walk_EnumDecl(node, file: File):
    name = node["name"] if "name" in node else ""
    fields = []
    for decl in node["inner"]:
        if decl["kind"] == "EnumConstantDecl":
            field_name = decl["name"]
            inner = None
            if "inner" in decl:
                inner = walk_Expression(decl["inner"][0])
            
            fields.append((field_name, inner))

    #if not name:
    prev = "0"
    for f in fields:
        file.GLOBALS[f[0]] = ConstDecl(f[0], PRIMITIVES["int"], f[1] if f[1] else prev)
        prev = f[0] + " + 1"

    record = Enum(name, fields)
    if name:
        file.TAGGED[name] = record
    file.STRUCT_IDS[node["id"]] = record

def is_anonymous(qual_type):
    return ("unnamed struct at" in qual_type or 
        "unnamed union" in qual_type or 
        "unnamed at" in qual_type or
        "anonymous at" in qual_type)

def walk_TypedefDecl(node, file: File):
    name = node["name"]
    inner = node["inner"][0]
    if "ownedTagDecl" in inner:
        id = inner["ownedTagDecl"]["id"]
        struct = file.STRUCT_IDS[id]
        struct.typename = name
        file.TYPEDEFS[name] = struct
        if not struct.name:
            incomplete_type = Walker(file).walk(parse(get_type(inner)))
            file.TAGGED[incomplete_type.name] = struct
    else:
        tpe = get_type(inner)
        if is_anonymous(tpe):
            record = file.last_record
        else:
            record = Walker(file).walk(parse(tpe))
        file.TYPEDEFS[name] = record

def walk_RecordDecl(node, file: File):
    name = node["name"] if "name" in node else ""

    fields = []
    if "inner" in node:
        for i, field in enumerate(node["inner"]):
            if field["kind"] == "FieldDecl":
                is_bitfield = field.get("isBitfield", False)
                bit_size = 0
                if is_bitfield:
                    bit_size = int(field["inner"][0]["value"])

                qual_type = get_type(field)
                if is_anonymous(qual_type):
                    tpe = file.last_record
                else:
                    tpe = Walker(file).walk(parse(qual_type))
                
                field_name = field.get("name", "" if is_bitfield else "_" + str(i))
                fields.append(Field(tpe, field_name, is_bitfield, bit_size))
            elif field["kind"] == "RecordDecl":
                file.last_record = walk_RecordDecl(field, file)
    
    if node["tagUsed"] == "struct":
        record = Struct(name, fields)
    else: record = Union(name, fields)

    file.last_record = record

    if name:
        file.TAGGED[name] = record
    file.STRUCT_IDS[node["id"]] = record

    return record

def walk_FunctionDecl(node, file: File):
    name = node["name"]
    ret = Walker(file).walk(parse(get_type(node)))
    if node.get("storageClass", None) != "static":
        variadic = node.get("variadic", False)
        if node.get("inline", False): return
        dllimport = False
        args = []
        if "inner" in node:
            for i, param in enumerate(node["inner"]):
                if param["kind"] == "ParmVarDecl":
                    argname = escape_name(param.get("name", "_" + str(i)))
                    tpe = Walker(file).walk(parse(get_type(param)))
                    args.append((argname, tpe))
                elif param["kind"] == "DLLImportAttr":
                    dllimport = True



        file.GLOBALS[name] = FunctionDecl(name, ret, args, variadic, dllimport)

def walk(node, file: File):
    if node["kind"] == "VarDecl": 
        walk_VarDecl(node, file)
    elif node["kind"] == "TypedefDecl":
        walk_TypedefDecl(node, file)
    elif node["kind"] == "FunctionDecl":
        walk_FunctionDecl(node, file)
    elif node["kind"] == "RecordDecl":
        walk_RecordDecl(node, file)
    elif node["kind"] == "EnumDecl":
        walk_EnumDecl(node, file)

ALL_DEFINITIONS = {}

def get_symbols(lib: str):
    if sys.platform == "win32":
        vswhere = os.environ["ProgramFiles(x86)"] + r"\Microsoft Visual Studio\Installer\vswhere.exe"
        dumpbin = subprocess.check_output([vswhere, "-latest", "-find", r"VC\Tools\**\x64\dumpbin.exe"]).splitlines()[0]
        winsdk_bat = subprocess.check_output([vswhere, "-latest", "-find", "**\winsdk.bat"]).splitlines()[0]
        os.environ["VSCMD_ARG_HOST_ARCH"] = "x64"
        os.environ["VSCMD_ARG_TGT_ARCH"] = "x64"
        env = dict([tuple(var.decode().split("=")) for var in subprocess.check_output([winsdk_bat, ">", "nul", "&&", "set"], shell = True).splitlines()])
        lib_path = env["WindowsSdkDir"] + "Lib\\" + env["WindowsSDKVersion"] + "um\\x64\\"
        dout = subprocess.check_output([dumpbin, "/exports", lib_path + lib]).decode().splitlines()
        
        symbols = []
        for i, line in enumerate(dout):
            if "ordinal" in line and "name" in line:
                for j in dout[i+2:]:
                    j = j.strip()
                    if len(j) == 0:
                        break
                    
                    sym = j.split("    ")
                    if len(sym) > 1:
                        sym = sym[1]
                    else: sym = sym[0]
                    symbols.append(sym)
                break
        return symbols
    return []

def process_module(name: str, *libs):
    included = []
    if len(libs) > 0:
        for lib in libs:
            included.extend(get_symbols(lib))


    folder = Path(__file__).parent
    platform = folder / ("windows" if sys.platform == "win32" else "macos" if sys.platform == "darwin" else "linux")

    if sys.platform == "win32":
        clang_bin = "clang"
    elif sys.platform == "darwin":
        clang_bin = "/opt/homebrew//Cellar/llvm@13/13.0.1_2//bin/clang"
    else: 
        clang_bin = "clang-13"
    clang_cmd = [clang_bin, "-Xclang", "-ast-dump=json", "-fsyntax-only"]
    if sys.platform == "win32":
        clang_cmd.append("--include-directory")
        clang_cmd.append(platform)
    if sys.platform == "darwin":
        clang_cmd.append("-I/opt/homebrew/opt/libffi/include")
        clang_cmd.append("-I/opt/homebrew/include")

    with open(platform / f"{name}.json", "w") as fp:
        clang_cmd.append(folder / f"{name}.h")
        p = subprocess.Popen(
            clang_cmd, 
            stdout = fp)
        p.wait()

    with open(platform / f"{name}.json", "r") as fp:
        data = json.load(fp)
        data = data["inner"]
    
    excluded = set()
    with open(folder / f"{name}.h", "r") as fp:
        for line in fp:
            if line.startswith("%EXCLUDE"):
                line = line.replace("%EXCLUDE", "")
                line = line.strip()
                excluded.update(line.split(" "))

    with open(platform / f"{name}.pr", "w") as fp,\
        open(platform / f"{name}_sym.pr", "w") as fp2:

        file = File(fp)

        for top_level in data:
            walk(top_level, file)
        
        file.GLOBALS = {k:v for k,v in file.GLOBALS.items() if k not in excluded and k not in ALL_DEFINITIONS}
        ALL_DEFINITIONS.update(file.GLOBALS)

        DEFS = {k:v for k,v in file.GLOBALS.items() if isinstance(v, FunctionDecl)}
        VARS = {k:v for k,v in file.GLOBALS.items() if isinstance(v, VarDecl)}
        CONSTS = {k:v for k,v in file.GLOBALS.items() if isinstance(v, ConstDecl)}

        for g in CONSTS.values():
            print(g.to_declaration(file), file = fp)

        for type in file.TYPEDEFS.values():
            type.print_references(file)
        for type in file.TAGGED.values():
            type.print_references(file)

        for g in DEFS.values():
            print(g.to_declaration(file), file = fp)
        for g in VARS.values():
            print(g.to_declaration(file), file = fp)

        filtered_defs = {k:v for k,v in DEFS.items() if not included or v.name in included }
        filtered_vars = {k:v for k,v in VARS.items() if not included or v.name in included }

        print(f"import {name}", file = fp2)
        print("import symbol", file = fp2)
        print(f"export var __SYMBOLS: [{len(filtered_defs) + len(filtered_vars)}; symbol::Symbol]", file = fp2)

        num_decls = 0
        for g in filtered_defs.values():
            print(g.to_symbol(num_decls, file), file = fp2)
            num_decls += 1
        for g in filtered_vars.values():
            print(g.to_symbol(num_decls, file), file = fp2)
            num_decls += 1

    return file

def main():
    if sys.platform != "win32":
        process_module("linux")

    process_module("cstd")
    process_module("ffi")

    if sys.platform == "win32":
        process_module("windows", "User32.lib", "Kernel32.lib", "Dbghelp.lib")

if __name__ == "__main__":
    main()