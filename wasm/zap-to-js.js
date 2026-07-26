#!/usr/bin/env node

/**
 * Zap to JavaScript Transpiler
 * Compiles Zap code to JavaScript for WebAssembly compilation
 */

const fs = require('fs');
const path = require('path');

class ZapToJS {
    constructor() {
        this.indent = 0;
        this.output = [];
        this.variables = new Set();
    }

    transpile(zapCode) {
        const lines = zapCode.split('\n');
        this.output = [];
        this.indent = 0;

        for (const line of lines) {
            this.transpileLine(line.trim());
        }

        return this.output.join('\n');
    }

    transpileLine(line) {
        // Skip empty lines and comments
        if (!line || line.startsWith('#')) {
            this.output.push('');
            return;
        }

        // Function definition
        if (line.startsWith('fn ')) {
            this.transpileFunction(line);
            return;
        }

        // Class definition
        if (line.startsWith('class ')) {
            this.transpileClass(line);
            return;
        }

        // If statement
        if (line.startsWith('if ')) {
            this.transpileIf(line);
            return;
        }

        // Else if
        if (line === 'el:') {
            this.output.push(this.getIndent() + '} else {');
            return;
        }

        // Else
        if (line === 'el:') {
            this.output.push(this.getIndent() + '} else {');
            return;
        }

        // While loop
        if (line.startsWith('while ')) {
            this.transpileWhile(line);
            return;
        }

        // For loop
        if (line.startsWith('for ')) {
            this.transpileFor(line);
            return;
        }

        // Return statement
        if (line.startsWith('ret ')) {
            const value = line.slice(4);
            this.output.push(this.getIndent() + `return ${this.transpileExpr(value)};`);
            return;
        }

        // Variable declaration
        if (line.startsWith('let ')) {
            this.transpileLet(line);
            return;
        }

        // Print statement
        if (line.startsWith('print(')) {
            this.transpilePrint(line);
            return;
        }

        // Regular expression
        this.output.push(this.getIndent() + this.transpileExpr(line) + ';');
    }

    transpileFunction(line) {
        const match = line.match(/^fn\s+(\w+)\s*\((.*?)\):?\s*$/);
        if (match) {
            const name = match[1];
            const params = match[2];
            this.output.push(this.getIndent() + `function ${name}(${params}) {`);
            this.indent++;
        }
    }

    transpileClass(line) {
        const match = line.match(/^class\s+(\w+):?\s*$/);
        if (match) {
            const name = match[1];
            this.output.push(this.getIndent() + `class ${name} {`);
            this.indent++;
        }
    }

    transpileIf(line) {
        const match = line.match(/^if\s+(.+):?\s*$/);
        if (match) {
            const condition = this.transpileExpr(match[1]);
            this.output.push(this.getIndent() + `if (${condition}) {`);
            this.indent++;
        }
    }

    transpileWhile(line) {
        const match = line.match(/^while\s+(.+):?\s*$/);
        if (match) {
            const condition = this.transpileExpr(match[1]);
            this.output.push(this.getIndent() + `while (${condition}) {`);
            this.indent++;
        }
    }

    transpileFor(line) {
        const match = line.match(/^for\s+(\w+)\s+in\s+(.+):?\s*$/);
        if (match) {
            const varName = match[1];
            const iterable = this.transpileExpr(match[2]);
            this.output.push(this.getIndent() + `for (const ${varName} of ${iterable}) {`);
            this.indent++;
        }
    }

    transpileLet(line) {
        const match = line.match(/^let\s+(\w+)\s*=\s*(.+)$/);
        if (match) {
            const name = match[1];
            const value = this.transpileExpr(match[2]);
            this.output.push(this.getIndent() + `let ${name} = ${value};`);
            this.variables.add(name);
        }
    }

    transpilePrint(line) {
        const match = line.match(/^print\((.+)\)$/);
        if (match) {
            const args = this.transpileExpr(match[1]);
            this.output.push(this.getIndent() + `console.log(${args});`);
        }
    }

    transpileExpr(expr) {
        expr = expr.trim();

        // String literals
        if (expr.startsWith('"') && expr.endsWith('"')) {
            return expr;
        }
        if (expr.startsWith("'") && expr.endsWith("'")) {
            return expr.replace(/'/g, '"');
        }

        // Number literals
        if (/^\d+(\.\d+)?$/.test(expr)) {
            return expr;
        }

        // Boolean literals
        if (expr === 'true') return 'true';
        if (expr === 'false') return 'false';
        if (expr === 'none') return 'null';

        // Operators
        expr = expr.replace(/\band\b/g, '&&');
        expr = expr.replace(/\bor\b/g, '||');
        expr = expr.replace(/\bnot\b/g, '!');

        // Function calls
        expr = expr.replace(/(\w+)\((.*?)\)/g, (match, name, args) => {
            if (name === 'len') return `Array.isArray(${args}) ? ${args}.length : ${args}.length`;
            if (name === 'str') return `String(${args})`;
            if (name === 'int') return `parseInt(${args})`;
            if (name === 'float') return `parseFloat(${args})`;
            if (name === 'range') return `Array.from({length: ${args}}, (_, i) => i)`;
            if (name === 'append') return `${args.split(',')[0]}.push(${args.split(',')[1]})`;
            return `${name}(${args})`;
        });

        // List literals
        expr = expr.replace(/\[(.*?)\]/g, (match, items) => {
            return `[${items}]`;
        });

        // Dict literals
        expr = expr.replace(/\{(.*?)\}/g, (match, items) => {
            return `{${items}}`;
        });

        return expr;
    }

    getIndent() {
        return '  '.repeat(this.indent);
    }
}

// CLI usage
if (require.main === module) {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        console.error('Usage: node zap-to-js.js <input.zap> [output.js]');
        process.exit(1);
    }

    const inputFile = args[0];
    const outputFile = args[1] || inputFile.replace('.zap', '.js');

    const zapCode = fs.readFileSync(inputFile, 'utf-8');
    const transpiler = new ZapToJS();
    const jsCode = transpiler.transpile(zapCode);

    fs.writeFileSync(outputFile, jsCode);
    console.log(`Compiled ${inputFile} -> ${outputFile}`);
}

module.exports = ZapToJS;
