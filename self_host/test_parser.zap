# test_parser.zap — Tests the self-hosted parser
import "self_host/tokens.zap"
import "self_host/parser.zap"

# Simple test code to tokenize + parse
test_code = "let x = 10\nlet y = 20"

# Tokenize it
toks = tokenize(test_code, "<test>")
print("Tokens:", len(toks))

for t in toks:
    print("  " + str(t.type) + ": " + str(t.value))

# Parse it
p = Parser(toks)
tree = p.parse()
print("Parse OK! Type:", type(tree))
print("Statements:", len(tree.stmts))
print("Errors:", p.errors)
