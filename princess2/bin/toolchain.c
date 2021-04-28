/* This file was compiled by the grace
   of your highness Princess Vic Nightfall
*/
#include "princess.h"
#ifndef _toolchain_H
#define _toolchain_H
#include "vector.c"
#include "util.c"
#include "buffer.c"
#include "map.c"
map_Map *toolchain_modules;
Array toolchain_include_path;
int toolchain_error_count;
typedef struct scope_Scope scope_Scope;
typedef struct parser_Node parser_Node;
DLL_EXPORT void toolchain_compile_file(string filename, string module);
DLL_EXPORT scope_Scope * toolchain_compile_module(parser_Node *module);
#include "lexer.c"
#include "parser.c"
#include "typechecking.c"
#include "scope.c"
#include "compiler.c"
#include "codegen.c"
#include "debug.c"
#include "builtins.c"
 string _8db3e3d6_find_module_file(parser_Node *module) {
    assert((((*module).kind) == parser_NodeKind_IDENTIFIER));
    vector_Vector *ident = (((*module).value).body);
    Array path = ((Array){PATH_MAX, calloc(PATH_MAX, (sizeof(char)))});
    int len = vector_length(ident);
    for (int i = 0;(i < len);(i += 1)) {
        string str = (*((string *)vector_get(ident, i)));
        concat((path.value), (((Array){3, "%s"}).value), (str.value));
        if ((i < (len - 1))) {
            concat((path.value), (((Array){3, "%s"}).value), (((Array){2, "/"}).value));
        }  ;
    }
    ;
    for (int i = 0;(i < (toolchain_include_path.size));(i += 1)) {
        Array module_path = ((Array){PATH_MAX, calloc(PATH_MAX, (sizeof(char)))});
        concat((module_path.value), (((Array){3, "%s"}).value), ((((string *)toolchain_include_path.value)[i]).value));
        concat((module_path.value), (((Array){7, "%s%s%s"}).value), (((Array){2, "/"}).value), (path.value), (((Array){4, ".pr"}).value));
        (module_path.size) = (((int64)strlen((module_path.value))) + ((int64)1));
        if (util_exists(module_path)) {
            return module_path;
        }  ;
    }
    ;
    return ((Array){1, ""});
};
DLL_EXPORT void toolchain_compile_file(string filename, string module) {
    FILE* fh = fopen((filename.value), (((Array){3, "rb"}).value));
    if ((!fh)) {
        fprintf(stderr, (((Array){7, "%s%s%s"}).value), (((Array){7, "File \""}).value), (filename.value), (((Array){17, "\" doesn't exist\x0a"""}).value));
    }  else {
        fseek(fh, 0, SEEK_END);
        int filesize = ftell(fh);
        rewind(fh);
        Array buf = ((Array){(filesize + 1), malloc((((int64)(sizeof(char))) * ((int64)(filesize + 1))))});
        fread((buf.value), (sizeof(char)), filesize, fh);
        (((char *)buf.value)[filesize]) = '\x00';
        fclose(fh);
        Array lines = util_split_lines(buf);
        lexer_TokenList *tokens = lexer_lex(buf);
        free((buf.value));
        parser_Node *node = parser_parse(tokens, lines, filename, module);
        scope_Scope *sc = scope_enter_scope(builtins_builtins);
        map_put(toolchain_modules, filename, sc);
        typechecking_typecheck(node, sc, filename, module);
        compiler_Result result = compiler_compile(node, filename, module);
        if ((toolchain_error_count == 0)) {
            codegen_gen(result, filename, module);
        }  ;
    };
};
DLL_EXPORT scope_Scope * toolchain_compile_module(parser_Node *module) {
    string filename = _8db3e3d6_find_module_file(module);
    string modulename = parser_identifier_to_str(module);
    if ((((filename.size) - 1) == 0)) {
        return NULL;
    }  ;
    scope_Scope *sc = ((scope_Scope *)map_get(toolchain_modules, filename));
    if ((!sc)) {
        toolchain_compile_file(filename, modulename);
        sc = map_get(toolchain_modules, filename);
    }  ;
    return sc;
};
DLL_EXPORT void toolchain_p_main(Array args) {
    ;
    toolchain_modules = map_make();
    toolchain_error_count = 0;
    typechecking_p_main(args);
    scope_p_main(args);
    compiler_p_main(args);
    codegen_p_main(args);
    debug_p_main(args);
    builtins_p_main(args);
};


#endif
