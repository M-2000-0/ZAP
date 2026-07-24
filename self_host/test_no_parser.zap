# test_no_parser.zap — Test without parser
import "self_host/lexer.zap"

fn main():
    print("start")
    let code = "fn add(a, b):\n    ret a + b"
    let lx = Lexer(code, "<test>")
    let toks = lx.tokenize()
    print("tokens: " + str(len(toks)))
    let i = 0
    while i < len(toks):
        print(str(toks[i].type) + " = " + str(toks[i].value))
        i = i + 1
    print("done")

main()
