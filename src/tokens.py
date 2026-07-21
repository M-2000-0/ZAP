from enum import Enum, auto

class TokenType(Enum):
    EOF = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    IDENTIFIER = auto()
    NUMBER = auto()
    STRING = auto()
    FLOAT = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    ARROW = auto()
    PIPE = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    POW = auto()
    MATMUL = auto()

    EQ = auto()
    EQEQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()

    AND = auto()
    OR = auto()
    NOT = auto()
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()

    # Core keywords
    KW_FN = auto()
    KW_LET = auto()
    KW_IF = auto()
    KW_EL = auto()
    KW_FOR = auto()
    KW_IN = auto()
    KW_WHILE = auto()
    KW_RET = auto()
    KW_TRUE = auto()
    KW_FALSE = auto()
    KW_NONE = auto()
    KW_AND = auto()
    KW_OR = auto()
    KW_NOT = auto()
    KW_IMPORT = auto()
    KW_FROM = auto()
    KW_CLASS = auto()
    KW_ASYNC = auto()
    KW_AWAIT = auto()
    KW_MATCH = auto()
    KW_INTEND = auto()
    KW_AT = auto()

    # Native constructs
    KW_SERVICE = auto()
    KW_DATABASE = auto()
    KW_API = auto()
    KW_PAGE = auto()
    KW_SCHEMA = auto()
    KW_MODEL = auto()
    KW_EXPOSE = auto()

    # AI-native features
    KW_REQUIRES = auto()
    KW_ENSURES = auto()
    KW_INVARIANT = auto()
    KW_EXPECT = auto()
    KW_PERMISSION = auto()
    KW_CONCURRENT = auto()
    KW_CHANNEL = auto()
    KW_GUARANTEES = auto()
    KW_VERSION = auto()
    KW_CHECK = auto()

KEYWORDS = {
    'fn': TokenType.KW_FN,
    'let': TokenType.KW_LET,
    'if': TokenType.KW_IF,
    'el': TokenType.KW_EL,
    'for': TokenType.KW_FOR,
    'in': TokenType.KW_IN,
    'while': TokenType.KW_WHILE,
    'ret': TokenType.KW_RET,
    'true': TokenType.KW_TRUE,
    'false': TokenType.KW_FALSE,
    'none': TokenType.KW_NONE,
    'and': TokenType.KW_AND,
    'or': TokenType.KW_OR,
    'not': TokenType.KW_NOT,
    'import': TokenType.KW_IMPORT,
    'from': TokenType.KW_FROM,
    'class': TokenType.KW_CLASS,
    'async': TokenType.KW_ASYNC,
    'await': TokenType.KW_AWAIT,
    'match': TokenType.KW_MATCH,
    'intend': TokenType.KW_INTEND,
    'service': TokenType.KW_SERVICE,
    'database': TokenType.KW_DATABASE,
    'api': TokenType.KW_API,
    'page': TokenType.KW_PAGE,
    'schema': TokenType.KW_SCHEMA,
    'model': TokenType.KW_MODEL,
    'expose': TokenType.KW_EXPOSE,
    'requires': TokenType.KW_REQUIRES,
    'ensures': TokenType.KW_ENSURES,
    'invariant': TokenType.KW_INVARIANT,
    'expect': TokenType.KW_EXPECT,
    'permission': TokenType.KW_PERMISSION,
    'concurrent': TokenType.KW_CONCURRENT,
    'channel': TokenType.KW_CHANNEL,
    'guarantees': TokenType.KW_GUARANTEES,
    'version': TokenType.KW_VERSION,
    'check': TokenType.KW_CHECK,
}


class Token:
    __slots__ = ('type', 'value', 'line', 'col')

    def __init__(self, type, value, line, col):
        self.type = type
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, L{self.line}:{self.col})"
