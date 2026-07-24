# test_parser_debug.zap — Debug parser with fn
import "self_host/lexer.zap"
import "self_host/parser.zap"

fn tokenize_code(code):
    let lx = Lexer(code, "<test>")
    let toks = lx.tokenize()
    ret toks

fn main():
    print("=== Debug Parser Test ===")

    # Test 1: let (known working)
    let code1 = "let x = 10"
    let toks1 = tokenize_code(code1)
    print("Test 1 tokens: " + str(len(toks1)))
    let p1 = Parser(toks1)
    let tree1 = p1.parse()
    print("Test 1: " + str(len(tree1.stmts)) + " stmts, " + str(len(p1.errors)) + " errors")

    # Test 2: fn - show tokens first
    let code2 = "fn add(a, b):\n    ret a + b"
    let toks2 = tokenize_code(code2)
    print("Test 2 tokens: " + str(len(toks2)))
    let i = 0
    while i < len(toks2):
        print("  " + str(toks2[i].type) + " = " + str(toks2[i].value) + " L" + str(toks2[i].line) + ":" + str(toks2[i].col))
        i = i + 1

    # Now parse
    let p2 = Parser(toks2)
    let tree2 = p2.parse()
    print("Test 2: " + str(len(tree2.stmts)) + " stmts, " + str(len(p2.errors)) + " errors")

    print("=== Done ===")

main()
