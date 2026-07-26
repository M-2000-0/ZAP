const vscode = require('vscode');
const { exec } = require('child_process');
const path = require('path');

/**
 * Activates the Zap language extension
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('Zap Language extension is now active!');

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('zap.runFile', runFile),
        vscode.commands.registerCommand('zap.runProject', runProject),
        vscode.commands.registerCommand('zap.format', formatDocument)
    );

    // Register language features
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider('zap', new ZapCompletionProvider(), '.', '(', '[', ','),
        vscode.languages.registerHoverProvider('zap', new ZapHoverProvider()),
        vscode.languages.registerDefinitionProvider('zap', new ZapDefinitionProvider()),
        vscode.languages.registerDocumentFormattingEditProvider('zap', new ZapFormatter()),
        vscode.languages.registerCodeLensProvider('zap', new ZapCodeLensProvider())
    );

    // Register diagnostic collection
    const diagnosticCollection = vscode.languages.createDiagnosticCollection('zap');
    context.subscriptions.push(diagnosticCollection);

    // Update diagnostics on document changes
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

/**
 * Runs the current Zap file
 */
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

    // Save the document first
    await document.save();

    const filePath = document.fileName;
    const config = vscode.workspace.getConfiguration('zap');
    const executablePath = config.get('executablePath', 'zap');

    const terminal = vscode.window.createTerminal('Zap');
    terminal.show();
    terminal.sendText(`${executablePath} run "${filePath}"`);
}

/**
 * Runs the Zap project
 */
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

/**
 * Formats the current document
 */
async function formatDocument() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        return;
    }

    const document = editor.document;
    const text = document.getText();
    
    // Simple Zap formatter
    const formatted = formatZapCode(text);
    
    const fullRange = new vscode.Range(
        document.positionAt(0),
        document.positionAt(text.length)
    );
    
    await editor.edit(editBuilder => {
        editBuilder.replace(fullRange, formatted);
    });
}

/**
 * Simple Zap code formatter
 * @param {string} code
 * @returns {string}
 */
function formatZapCode(code) {
    const lines = code.split('\n');
    const formatted = [];
    let indentLevel = 0;
    const indentSize = 2;

    for (let line of lines) {
        const trimmed = line.trim();
        
        // Skip empty lines
        if (trimmed === '') {
            formatted.push('');
            continue;
        }

        // Decrease indent for certain keywords
        if (/^(el:|catch:|finally:)/.test(trimmed)) {
            indentLevel = Math.max(0, indentLevel - 1);
        }

        // Add the line with proper indentation
        formatted.push(' '.repeat(indentLevel * indentSize) + trimmed);

        // Increase indent for block starters
        if (/^(fn|class|if|elif|else|for|while|match|test|doc|try|catch|finally|service|api|schema|database|channel|concurrent|check).*:\s*$/.test(trimmed)) {
            indentLevel++;
        }
    }

    return formatted.join('\n');
}

/**
 * Updates diagnostics for a document
 * @param {vscode.TextDocument} document
 * @param {vscode.DiagnosticCollection} diagnosticCollection
 */
function updateDiagnostics(document, diagnosticCollection) {
    if (document.languageId !== 'zap') {
        return;
    }

    const diagnostics = [];
    const text = document.getText();
    const lines = text.split('\n');

    lines.forEach((line, index) => {
        // Check for common errors
        if (line.includes('return ') && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "ret" instead of "return" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if (line.includes('elif ') && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "el:" + "if" instead of "elif" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        if ((line.includes('&&') || line.includes('||')) && !line.trimStart().startsWith('#')) {
            diagnostics.push({
                range: new vscode.Range(index, 0, index, line.length),
                message: 'Use "and"/"or" instead of "&&"/"||" in Zap',
                severity: vscode.DiagnosticSeverity.Warning,
                source: 'zap'
            });
        }

        // Check for missing colon after block starters
        if (/^\s*(fn|class|if|elif|else|for|while|match|test|doc|try|catch|finally)\s+.*[^:]\s*$/.test(line)) {
            if (!line.includes('#') && !line.includes('"') && !line.includes("'")) {
                diagnostics.push({
                    range: new vscode.Range(index, 0, index, line.length),
                    message: 'Missing colon after block statement',
                    severity: vscode.DiagnosticSeverity.Error,
                    source: 'zap'
                });
            }
        }
    });

    diagnosticCollection.set(document.uri, diagnostics);
}

/**
 * Zap Completion Provider
 */
class ZapCompletionProvider {
    provideCompletionItems(document, position, token, context) {
        const completions = [];

        // Keywords
        const keywords = [
            'fn', 'class', 'if', 'el:', 'else', 'elif', 'for', 'in', 'while',
            'ret', 'return', 'break', 'continue', 'pass', 'let', 'mut',
            'and', 'or', 'not', 'true', 'false', 'none',
            'import', 'from', 'as', 'try', 'catch', 'throw', 'finally',
            'match', 'test', 'doc', 'schema', 'api', 'service', 'database',
            'channel', 'concurrent', 'check', 'expect', 'requires', 'ensures',
            'invariant', 'permission', 'version', 'expose', 'enum', 'type'
        ];

        keywords.forEach(keyword => {
            completions.push({
                label: keyword,
                kind: vscode.CompletionItemKind.Keyword,
                insertText: keyword,
                detail: 'Zap keyword'
            });
        });

        // Built-in functions
        const builtins = [
            'print', 'input', 'len', 'str', 'int', 'float', 'type', 'range',
            'append', 'remove', 'sort', 'reverse', 'map', 'filter', 'reduce',
            'zip', 'enumerate', 'abs', 'min', 'max', 'sum', 'round',
            'hash', 'uuid', 'random', 'time', 'date', 'now', 'sleep',
            'read_file', 'write_file', 'file_exists', 'list_dir',
            'http_get', 'http_post', 'json_parse', 'json_stringify',
            'base64_encode', 'base64_decode', 'sha256', 'md5'
        ];

        builtins.forEach(builtin => {
            completions.push({
                label: builtin,
                kind: vscode.CompletionItemKind.Function,
                insertText: builtin,
                detail: 'Zap builtin',
                documentation: new vscode.MarkdownString(`Built-in function: \`${builtin}\``)
            });
        });

        // Snippets
        completions.push({
            label: 'fn',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('fn ${1:name}(${2:params}):\n\t${3:body}'),
            detail: 'Function definition',
            documentation: new vscode.MarkdownString('Define a function')
        });

        completions.push({
            label: 'class',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('class ${1:Name}:\n\tfn init(self${2:, params}):\n\t\t${3:body}'),
            detail: 'Class definition',
            documentation: new vscode.MarkdownString('Define a class')
        });

        completions.push({
            label: 'if',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('if ${1:condition}:\n\t${2:body}'),
            detail: 'If statement',
            documentation: new vscode.MarkdownString('If statement')
        });

        completions.push({
            label: 'el:',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('el:\n\t${1:body}'),
            detail: 'Else statement',
            documentation: new vscode.MarkdownString('Else clause')
        });

        completions.push({
            label: 'for',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('for ${1:item} in ${2:iterable}:\n\t${3:body}'),
            detail: 'For loop',
            documentation: new vscode.MarkdownString('For loop')
        });

        completions.push({
            label: 'while',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('while ${1:condition}:\n\t${2:body}'),
            detail: 'While loop',
            documentation: new vscode.MarkdownString('While loop')
        });

        completions.push({
            label: 'match',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('match ${1:value}:\n\t${2:case}: ${3:result}\nel:\n\t${4:default}'),
            detail: 'Match statement',
            documentation: new vscode.MarkdownString('Pattern matching')
        });

        completions.push({
            label: 'try',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('try:\n\t${1:body}\ncatch ${2:err}:\n\t${3:error handling}'),
            detail: 'Try-catch',
            documentation: new vscode.MarkdownString('Error handling')
        });

        completions.push({
            label: 'schema',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('schema ${1:Name}:\n\t${2:field}: ${3:type}'),
            detail: 'Schema definition',
            documentation: new vscode.MarkdownString('Define a data schema')
        });

        completions.push({
            label: 'api',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('api ${1:GET} "${2:/path}":\n\t${3:handler}'),
            detail: 'API endpoint',
            documentation: new vscode.MarkdownString('Define an API endpoint')
        });

        completions.push({
            label: 'service',
            kind: vscode.CompletionItemKind.Snippet,
            insertText: new vscode.SnippetString('service ${1:Name}:\n\t${2:body}'),
            detail: 'Service definition',
            documentation: new vscode.MarkdownString('Define a service')
        });

        return completions;
    }
}

/**
 * Zap Hover Provider
 */
class ZapHoverProvider {
    provideHover(document, position, token) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) {
            return null;
        }

        const text = document.getText(word);
        
        // Built-in function documentation
        const docs = {
            'print': 'Print output to console\n\n```zap\nprint("Hello, World!")\n```',
            'len': 'Get length of string or list\n\n```zap\nlen([1, 2, 3])  # 3\n```',
            'str': 'Convert to string\n\n```zap\nstr(42)  # "42"\n```',
            'int': 'Convert to integer\n\n```zap\nint("42")  # 42\n```',
            'float': 'Convert to float\n\n```zap\nfloat("3.14")  # 3.14\n```',
            'range': 'Generate a range of numbers\n\n```zap\nrange(5)  # [0, 1, 2, 3, 4]\n```',
            'map': 'Apply function to each element\n\n```zap\nmap([1, 2, 3], x => x * 2)  # [2, 4, 6]\n```',
            'filter': 'Filter elements by condition\n\n```zap\nfilter([1, 2, 3], x => x > 1)  # [2, 3]\n```',
            'append': 'Add element to list\n\n```zap\nlet lst = [1, 2]\nlst.append(3)  # [1, 2, 3]\n```',
            'fn': 'Define a function\n\n```zap\nfn add(a, b):\n\tret a + b\n```',
            'class': 'Define a class\n\n```zap\nclass Dog:\n\tfn init(self, name):\n\t\tself.name = name\n```',
            'if': 'Conditional statement\n\n```zap\nif x > 0:\n\tprint("positive")\n```',
            'for': 'For loop\n\n```zap\nfor i in range(5):\n\tprint(i)\n```',
            'while': 'While loop\n\n```zap\nwhile x < 10:\n\tx = x + 1\n```',
            'match': 'Pattern matching\n\n```zap\nmatch status:\n\t"active": print("active")\n\t"inactive": print("inactive")\n```',
            'try': 'Error handling\n\n```zap\ntry:\n\tlet result = risky_operation()\ncatch err:\n\tprint("Error: " + err)\n```',
        };

        if (docs[text]) {
            return new vscode.Hover(new vscode.MarkdownString(docs[text]));
        }

        return null;
    }
}

/**
 * Zap Definition Provider
 */
class ZapDefinitionProvider {
    provideDefinition(document, position, token) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) {
            return null;
        }

        const text = document.getText(word);
        const fullText = document.getText();
        const lines = fullText.split('\n');

        // Search for function/class definitions
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Match fn definitions
            const fnMatch = line.match(/^\s*fn\s+(\w+)\s*\(/);
            if (fnMatch && fnMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }

            // Match class definitions
            const classMatch = line.match(/^\s*class\s+(\w+)/);
            if (classMatch && classMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }

            // Match variable assignments
            const varMatch = line.match(/^\s*let\s+(\w+)\s*=/);
            if (varMatch && varMatch[1] === text) {
                return new vscode.Location(document.uri, new vscode.Position(i, 0));
            }
        }

        return null;
    }
}

/**
 * Zap Formatter
 */
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

/**
 * Zap Code Lens Provider
 */
class ZapCodeLensProvider {
    provideCodeLenses(document, token) {
        const lenses = [];
        const text = document.getText();
        const lines = text.split('\n');

        lines.forEach((line, index) => {
            // Add "Run" lens for functions
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

/**
 * Deactivates the extension
 */
function deactivate() {
    console.log('Zap Language extension is now deactivated');
}

module.exports = {
    activate,
    deactivate
};
