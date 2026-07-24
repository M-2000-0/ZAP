# test_parser_debug2.zap — Minimal debug
import "self_host/lexer.zap"
import "self_host/parser.zap"

fn tokenize_code(code):
    let lx = Lexer(code, "<test>")
    let toks = lx.tokenize()
    ret toks

fn main():
    print("start")

    let code2 = "fn add(a, b):\n    ret a + b"
    let toks2 = tokenize_code(code2)
    print("tokens count: " + str(len(toks2)))

    let i = 0
    while i < len(toks2):
        let t = toks2[i]
        print("tok: " + str(t.typ) + " = " + str(t.value))
        i = i + 1

    print("done")

main()
