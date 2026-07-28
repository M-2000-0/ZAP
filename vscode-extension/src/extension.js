const vscode = require('vscode');

function activate(context) {
    context.subscriptions.push(
        vscode.commands.registerCommand('zap.runFile', runFile),
        vscode.commands.registerCommand('zap.runProject', runProject),
        vscode.commands.registerCommand('zap.format', formatDocument)
    );

    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider('zap', new ZapCompletionProvider(), '.', '(', '[', ','),
        vscode.languages.registerHoverProvider('zap', new ZapHoverProvider()),
        vscode.languages.registerDefinitionProvider('zap', new ZapDefinitionProvider()),
        vscode.languages.registerDocumentFormattingEditProvider('zap', new ZapFormatter()),
        vscode.languages.registerCodeLensProvider('zap', new ZapCodeLensProvider())
    );

    const diagnosticCollection = vscode.languages.createDiagnosticCollection('zap');
    context.subscriptions.push(diagnosticCollection);

    if (vscode.window.activeTextEditor) {
        updateDiagnostics(vscode.window.activeTextEditor.document, diagnosticCollection);
    }

    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(document => {
            updateDiagnostics(document, diagnosticCollection);
        }),
        vscode.workspace.onDidOpenTextDocument(document => {
            updateDiagnostics(document, diagnosticCollection);
        }),
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                updateDiagnostics(editor.document, diagnosticCollection);
            }
        })
    );
}

async function runFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }

    const document = editor.document;
    if (document.languageId !== 'zap') {
        vscode.window.showErrorMessage('Not a Zap file');
        return;
    }

    await document.save();
    const filePath = document.fileName;
    const config = vscode.workspace.getConfiguration('zap');
    const executablePath = config.get('executablePath', 'zap');

    const terminal = vscode.window.createTerminal('Zap');
    terminal.show();
    terminal.sendText(`${executablePath} run "${filePath}"`);
}

async function runProject() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const rootPath = workspaceFolders[0].uri.fsPath;
    const config = vscode.workspace.getConfiguration('zap');
    const executablePath = config.get('executablePath', 'zap');

    const terminal = vscode.window.createTerminal('Zap Project');
    terminal.show();
    terminal.sendText(`cd "${rootPath}" && ${executablePath} run .`);
}

async function formatDocument() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;

    const document = editor.document;
    const text = document.getText();
    const formatted = formatZapCode(text);

    const fullRange = new vscode.Range(
        document.positionAt(0),
        document.positionAt(text.length)
    );

    await editor.edit(editBuilder => {
        editBuilder.replace(fullRange, formatted);
    });
}

function formatZapCode(code) {
    const lines = code.split('\n');
    const formatted = [];
    let indentLevel = 0;
    const indentSize = 2;

    for (let line of lines) {
        const trimmed = line.trim();

        if (trimmed === '') {
            formatted.push('');
            continue;
        }

        if (/^(el:)/.test(trimmed)) {
            indentLevel = Math.max(0, indentLevel - 1);
        }

        formatted.push(' '.repeat(indentLevel * indentSize) + trimmed);

        if (/^(fn|class|if|el:\s*if|for|while|match|test|doc|check)\b.*:\s*$/.test(trimmed)) {
            indentLevel++;
        }
    }

    return formatted.join('\n');
}

function updateDiagnostics(document, diagnosticCollection) {
    if (document.languageId !== 'zap') return;

    const diagnostics = [];
    const text = document.getText();
    const lines = text.split('\n');

    lines.forEach((line, index) => {
        if (line.includes('return ') && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "ret" instead of "return" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if (/\belif\b/.test(line) && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "el: if" (on two lines) instead of "elif" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if ((/\&\&/.test(line) || /\|\|/.test(line)) && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "and"/"or" instead of "&&"/"||" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if (/\bfunction\b/.test(line) && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "fn" instead of "function" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if (/\bthis\b/.test(line) && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "self" instead of "this" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if (/^\s*(fn|class|if|for|while)\s+.*[^:]\s*$/.test(line)) {
            if (!line.includes('#') && !line.includes('"') && !line.includes("'")) {
                diagnostics.push({
                    range: new vscode.Range(index, 0, index, line.length),
                    message: 'Missing colon at end of block statement',
                    severity: vscode.DiagnosticSeverity.Error,
                    source: 'zap'
                });
            }
        }
    });

    diagnosticCollection.set(document.uri, diagnostics);
}

class ZapCompletionProvider {
    provideCompletionItems(document, position, token, context) {
        const completions = [];

        const keywords = [
            'fn', 'class', 'if', 'el:', 'for', 'in', 'while',
            'ret', 'break', 'continue', 'let', 'mut',
            'and', 'or', 'not', 'true', 'false', 'none',
            'import', 'from', 'as', 'expose',
            'match', 'test', 'doc', 'check', 'expect',
            'type', 'enum', 'version', 'channel', 'schema',
            'api', 'service', 'database', 'concurrent'
        ];

        keywords.forEach(keyword => {
            completions.push({
                label: keyword,
                kind: vscode.CompletionItemKind.Keyword,
                insertText: keyword,
                detail: 'Zap keyword'
            });
        });

        const builtins = [
            'print', 'len', 'str', 'int', 'float', 'list', 'type', 'range',
            'isinstance', 'abs', 'max', 'min', 'sum', 'round',
            'map', 'filter', 'random', 'randint',
            'exp', 'log', 'sin', 'cos', 'floor', 'ceil', 'sqrt',
            'say', 'show', 'ask', 'now', 'wait', 'clear', 'today',
            'format', 'json_parse', 'json_stringify', 'json_load', 'json_save',
            'csv_load', 'csv_save', 'http_get', 'http_post', 'http_server',
            'web_fetch', 'download', 'image_load', 'image_save',
            'element', 'html', 'render', 'signal', 'effect',
            'serve', 'config', 'watch', 'run',
            'par_map', 'par_filter', 'par_for',
            'db_open', 'db_query', 'db_exec', 'db_close',
            'tensor', 'zeros', 'ones', 'reshape',
            'pmap', 'parallel', 'retry', 'exit'
        ];

        builtins.forEach(builtin => {
            completions.push({
                label: builtin,
                kind: vscode.CompletionItemKind.Function,
                insertText: builtin,
                detail: 'Zap builtin'
            });
        });

        completions.push({
            label: 'fn',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('fn ${1:name}(${2:params}):\n  ${3:body}'),
            detail: 'Function definition'
        });

        completions.push({
            label: 'class',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('class ${1:Name}:\n  fn init(self${2:, params}):\n    ${3:body}'),
            detail: 'Class definition'
        });

        completions.push({
            label: 'if',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('if ${1:condition}:\n  ${2:body}'),
            detail: 'If statement'
        });

        completions.push({
            label: 'el:',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('el:\n  ${1:body}'),
            detail: 'Else clause'
        });

        completions.push({
            label: 'el: if',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('el: if ${1:condition}:\n  ${2:body}'),
            detail: 'Else-if clause'
        });

        completions.push({
            label: 'for',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('for ${1:item} in ${2:iterable}:\n  ${3:body}'),
            detail: 'For loop'
        });

        completions.push({
            label: 'while',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('while ${1:condition}:\n  ${2:body}'),
            detail: 'While loop'
        });

        completions.push({
            label: 'match',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('match ${1:value}:\n  ${2:pattern}: ${3:result}\nel:\n  ${4:default}'),
            detail: 'Pattern matching'
        });

        completions.push({
            label: 'test',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('test ${1:name}():\n  ${2:body}'),
            detail: 'Test definition'
        });

        return completions;
    }
}

class ZapHoverProvider {
    provideHover(document, position, token) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) return null;

        const text = document.getText(word);

        const docs = {
            'print': 'Print output to console\n\n```zap\nprint("Hello, World!")\n```',
            'len': 'Get length of string or list\n\n```zap\nlen([1, 2, 3])  # 3\n```',
            'str': 'Convert to string\n\n```zap\nstr(42)  # "42"\n```',
            'int': 'Convert to integer\n\n```zap\nint("42")  # 42\n```',
            'float': 'Convert to float\n\n```zap\nfloat("3.14")  # 3.14\n```',
            'range': 'Generate a range of numbers\n\n```zap\nrange(5)  # [0, 1, 2, 3, 4]\n```',
            'abs': 'Absolute value\n\n```zap\nabs(-5)  # 5\n```',
            'sqrt': 'Square root\n\n```zap\nsqrt(9)  # 3.0\n```',
            'map': 'Apply function to each element\n\n```zap\nmap([1, 2, 3], double)  # [2, 4, 6]\n```',
            'filter': 'Filter elements by condition\n\n```zap\nfilter([1, 2, 3], is_even)  # [2]\n```',
            'fn': 'Define a function\n\n```zap\nfn add(a, b):\n  ret a + b\n```',
            'class': 'Define a class\n\n```zap\nclass Dog:\n  fn init(self, name):\n    self.name = name\n```',
            'if': 'Conditional statement\n\n```zap\nif x > 0:\n  print("positive")\n```',
            'el:': 'Else clause\n\n```zap\nif x > 0:\n  print("positive")\nel:\n  print("non-positive")\n```',
            'for': 'For loop\n\n```zap\nfor i in range(5):\n  print(i)\n```',
            'while': 'While loop\n\n```zap\nwhile x < 10:\n  x = x + 1\n```',
            'ret': 'Return a value\n\n```zap\nfn add(a, b):\n  ret a + b\n```',
            'let': 'Declare a variable\n\n```zap\nlet x = 42\n```',
            'self': 'Reference to current class instance\n\n```zap\nclass Dog:\n  fn init(self, name):\n    self.name = name\n```',
        };

        if (docs[text]) {
            return new vscode.Hover(new vscode.MarkdownString(docs[text]));
        }

        return null;
    }
}

class ZapDefinitionProvider {
    provideDefinition(document, position, token) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) return null;

        const text = document.getText(word);
        const lines = document.getText().split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            const fnMatch = line.match(/^\s*fn\s+(\w+)\s*\(/);
            if (fnMatch && fnMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }

            const classMatch = line.match(/^\s*class\s+(\w+)/);
            if (classMatch && classMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }

            const varMatch = line.match(/^\s*let\s+(\w+)\s*=/);
            if (varMatch && varMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }
        }

        return null;
    }
}

class ZapFormatter {
    provideDocumentFormattingEdits(document, options, token) {
        const edits = [];
        const text = document.getText();
        const formatted = formatZapCode(text);

        if (text !== formatted) {
            const fullRange = new vscode.Range(
                document.positionAt(0),
                document.positionAt(text.length)
            );
            edits.push(vscode.TextEdit.replace(fullRange, formatted));
        }

        return edits;
    }
}

class ZapCodeLensProvider {
    provideCodeLenses(document, token) {
        const lenses = [];
        const lines = document.getText().split('\n');

        lines.forEach((line, index) => {
            const fnMatch = line.match(/^\s*fn\s+(\w+)\s*\(/);
            if (fnMatch) {
                const range = new vscode.Range(index, 0, index, line.length);
                lenses.push(new vscode.CodeLens(range, {
                    title: 'Run',
                    command: 'zap.runFile',
                    tooltip: 'Run this file'
                }));
            }
        });

        return lenses;
    }
}

function deactivate() {}

module.exports = { activate, deactivate };
