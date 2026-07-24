# test_ast.zap — Simple test
import "self_host/ast_nodes.zap"
print("AST import OK")
let x = LetStmt("a", Literal(42))
print("LetStmt:", x)
