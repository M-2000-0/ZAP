# test_parser_with_py_tokens.zap — Test parser using Python-generated tokens
import "self_host/parser.zap"

fn make_token(typ, val, ln, cl):
    ret {"type": typ, "value": val, "line": ln, "col": cl}

fn test_let():
    let tokens = [
        make_token("KW_LET", "let", 1, 1),
        make_token("IDENTIFIER", "x", 1, 5),
        make_token("EQ", "=", 1, 7),
        make_token("NUMBER", 10, 1, 9),
        make_token("NEWLINE", "\n", 1, 11),
        make_token("KW_LET", "let", 2, 1),
        make_token("IDENTIFIER", "y", 2, 5),
        make_token("EQ", "=", 2, 7),
        make_token("NUMBER", 20, 2, 9),
        make_token("NEWLINE", "\n", 2, 11),
        make_token("EOF", none, 3, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("let test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_fn_def():
    let tokens = [
        make_token("KW_FN", "fn", 1, 1),
        make_token("IDENTIFIER", "add", 1, 4),
        make_token("LPAREN", "(", 1, 7),
        make_token("IDENTIFIER", "a", 1, 8),
        make_token("COMMA", ",", 1, 9),
        make_token("IDENTIFIER", "b", 1, 11),
        make_token("RPAREN", ")", 1, 12),
        make_token("COLON", ":", 1, 13),
        make_token("NEWLINE", "\n", 1, 14),
        make_token("INDENT", 4, 2, 1),
        make_token("KW_RET", "ret", 2, 5),
        make_token("IDENTIFIER", "a", 2, 9),
        make_token("PLUS", "+", 2, 11),
        make_token("IDENTIFIER", "b", 2, 13),
        make_token("NEWLINE", "\n", 2, 14),
        make_token("DEDENT", 0, 3, 1),
        make_token("EOF", none, 3, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("fn test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_if_else():
    let tokens = [
        make_token("KW_IF", "if", 1, 1),
        make_token("IDENTIFIER", "x", 1, 4),
        make_token("GT", ">", 1, 6),
        make_token("NUMBER", 10, 1, 8),
        make_token("COLON", ":", 1, 10),
        make_token("NEWLINE", "\n", 1, 11),
        make_token("INDENT", 4, 2, 1),
        make_token("IDENTIFIER", "print", 2, 5),
        make_token("LPAREN", "(", 2, 10),
        make_token("STRING", "big", 2, 11),
        make_token("RPAREN", ")", 2, 16),
        make_token("NEWLINE", "\n", 2, 17),
        make_token("DEDENT", 0, 3, 1),
        make_token("KW_EL", "el", 3, 1),
        make_token("COLON", ":", 3, 3),
        make_token("NEWLINE", "\n", 3, 4),
        make_token("INDENT", 4, 4, 1),
        make_token("IDENTIFIER", "print", 4, 5),
        make_token("LPAREN", "(", 4, 10),
        make_token("STRING", "small", 4, 11),
        make_token("RPAREN", ")", 4, 18),
        make_token("NEWLINE", "\n", 4, 19),
        make_token("DEDENT", 0, 5, 1),
        make_token("EOF", none, 5, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("if/else test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_for_loop():
    let tokens = [
        make_token("KW_FOR", "for", 1, 1),
        make_token("IDENTIFIER", "i", 1, 5),
        make_token("KW_IN", "in", 1, 7),
        make_token("IDENTIFIER", "range", 1, 10),
        make_token("LPAREN", "(", 1, 15),
        make_token("NUMBER", 5, 1, 16),
        make_token("RPAREN", ")", 1, 17),
        make_token("COLON", ":", 1, 18),
        make_token("NEWLINE", "\n", 1, 19),
        make_token("INDENT", 4, 2, 1),
        make_token("IDENTIFIER", "print", 2, 5),
        make_token("LPAREN", "(", 2, 10),
        make_token("IDENTIFIER", "i", 2, 11),
        make_token("RPAREN", ")", 2, 12),
        make_token("NEWLINE", "\n", 2, 13),
        make_token("DEDENT", 0, 3, 1),
        make_token("EOF", none, 3, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("for test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_while_loop():
    let tokens = [
        make_token("KW_WHILE", "while", 1, 1),
        make_token("IDENTIFIER", "x", 1, 7),
        make_token("GT", ">", 1, 9),
        make_token("NUMBER", 0, 1, 11),
        make_token("COLON", ":", 1, 12),
        make_token("NEWLINE", "\n", 1, 13),
        make_token("INDENT", 4, 2, 1),
        make_token("IDENTIFIER", "x", 2, 5),
        make_token("EQ", "=", 2, 7),
        make_token("IDENTIFIER", "x", 2, 9),
        make_token("MINUS", "-", 2, 11),
        make_token("NUMBER", 1, 2, 13),
        make_token("NEWLINE", "\n", 2, 14),
        make_token("DEDENT", 0, 3, 1),
        make_token("EOF", none, 3, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("while test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_expressions():
    let tokens = [
        make_token("IDENTIFIER", "x", 1, 1),
        make_token("EQ", "=", 1, 3),
        make_token("NUMBER", 1, 1, 5),
        make_token("PLUS", "+", 1, 7),
        make_token("NUMBER", 2, 1, 9),
        make_token("STAR", "*", 1, 11),
        make_token("NUMBER", 3, 1, 13),
        make_token("NEWLINE", "\n", 1, 14),
        make_token("EOF", none, 2, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("expr test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_list_and_dict():
    let tokens = [
        make_token("IDENTIFIER", "x", 1, 1),
        make_token("EQ", "=", 1, 3),
        make_token("LBRACKET", "[", 1, 5),
        make_token("NUMBER", 1, 1, 6),
        make_token("COMMA", ",", 1, 7),
        make_token("NUMBER", 2, 1, 9),
        make_token("COMMA", ",", 1, 10),
        make_token("NUMBER", 3, 1, 12),
        make_token("RBRACKET", "]", 1, 13),
        make_token("NEWLINE", "\n", 1, 14),
        make_token("EOF", none, 2, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("list test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_method_call():
    let tokens = [
        make_token("IDENTIFIER", "obj", 1, 1),
        make_token("DOT", ".", 1, 4),
        make_token("IDENTIFIER", "method", 1, 5),
        make_token("LPAREN", "(", 1, 11),
        make_token("IDENTIFIER", "arg1", 1, 12),
        make_token("COMMA", ",", 1, 16),
        make_token("IDENTIFIER", "arg2", 1, 18),
        make_token("RPAREN", ")", 1, 22),
        make_token("NEWLINE", "\n", 1, 23),
        make_token("EOF", none, 2, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("method call test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_index():
    let tokens = [
        make_token("IDENTIFIER", "x", 1, 1),
        make_token("EQ", "=", 1, 3),
        make_token("IDENTIFIER", "arr", 1, 5),
        make_token("LBRACKET", "[", 1, 8),
        make_token("NUMBER", 0, 1, 9),
        make_token("RBRACKET", "]", 1, 10),
        make_token("NEWLINE", "\n", 1, 11),
        make_token("EOF", none, 2, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("index test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn test_class():
    let tokens = [
        make_token("KW_CLASS", "class", 1, 1),
        make_token("IDENTIFIER", "Dog", 1, 7),
        make_token("COLON", ":", 1, 10),
        make_token("NEWLINE", "\n", 1, 11),
        make_token("INDENT", 4, 2, 1),
        make_token("KW_FN", "fn", 2, 5),
        make_token("IDENTIFIER", "bark", 2, 8),
        make_token("LPAREN", "(", 2, 12),
        make_token("IDENTIFIER", "self", 2, 13),
        make_token("RPAREN", ")", 2, 17),
        make_token("COLON", ":", 2, 18),
        make_token("NEWLINE", "\n", 2, 19),
        make_token("INDENT", 8, 3, 1),
        make_token("IDENTIFIER", "print", 3, 9),
        make_token("LPAREN", "(", 3, 14),
        make_token("STRING", "woof", 3, 15),
        make_token("RPAREN", ")", 3, 21),
        make_token("NEWLINE", "\n", 3, 22),
        make_token("DEDENT", 0, 4, 1),
        make_token("DEDENT", 0, 5, 1),
        make_token("EOF", none, 5, 1)
    ]
    let p = Parser(tokens)
    let tree = p.parse()
    print("class test: " + str(len(tree.stmts)) + " stmts, " + str(len(p.errors)) + " errors")

fn main():
    print("=== Parser Comprehensive Test ===")
    test_let()
    test_fn_def()
    test_if_else()
    test_for_loop()
    test_while_loop()
    test_expressions()
    test_list_and_dict()
    test_method_call()
    test_index()
    test_class()
    print("=== All parser tests done ===")

main()
