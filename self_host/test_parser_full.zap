# test_parser_full.zap — Comprehensive parser test
import "self_host/lexer.zap"
import "self_host/parser.zap"

fn tokenize_code(code):
    let lx = Lexer(code, "<test>")
    let toks = lx.tokenize()
    ret toks

fn test_let():
    let code = "let x = 10\nlet y = 20\nlet z = x + y"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("let test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_fn_def():
    let code = "fn add(a, b):\n    ret a + b"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("fn test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_if_else():
    let code = "if x > 10:\n    print('big')\nel:\n    print('small')"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("if/else test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_for_loop():
    let code = "for i in range(5):\n    print(i)"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("for test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_while_loop():
    let code = "while x > 0:\n    x = x - 1"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("while test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_class():
    let code = "class Dog:\n    fn bark(self):\n        print('woof')"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("class test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_expressions():
    let code = "x = 1 + 2 * 3\ny = (a + b) * c"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("expr test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_ret():
    let code = "fn greet():\n    ret 'hello'"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("ret test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_import():
    let code = 'import "lib/std.zap"'
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("import test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_list_literal():
    let code = "x = [1, 2, 3]"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("list test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_dict_literal():
    let code = 'x = {"a": 1, "b": 2}'
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("dict test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_method_call():
    let code = "obj.method(arg1, arg2)"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("method call test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_index():
    let code = "x = arr[0]"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("index test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_match():
    let code = "match x:\n    1:\n        print('one')\n    2:\n        print('two')\nel:\n        print('other')"
    let toks = tokenize_code(code)
    let p = Parser(toks)
    let tree = p.parse()
    print("match test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn main():
    print("=== Parser Comprehensive Test ===")
    test_let()
    test_fn_def()
    test_if_else()
    test_for_loop()
    test_while_loop()
    test_class()
    test_expressions()
    test_ret()
    test_import()
    test_list_literal()
    test_dict_literal()
    test_method_call()
    test_index()
    test_match()
    print("=== All parser tests done ===")

main()
