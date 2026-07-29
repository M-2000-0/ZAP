#!/usr/bin/env node

const fs = require('fs');

class ZapToJS {
    constructor() {
        this.blocks = [];
        this.output = [];
        this.classNames = new Set();
    }

    transpile(zapCode) {
        const lines = zapCode.split('\n');
        this.output = [];
        this.blocks = [];
        this.classNames = new Set();

        for (const raw of lines) {
            if (raw.trim() === '' || raw.trim().startsWith('#')) {
                this.output.push('');
                continue;
            }
            const indent = raw.search(/\S/);
            const line = raw.trim();

            const cm = line.match(/^class\s+(\w+):?\s*$/);
            if (cm) this.classNames.add(cm[1]);

            if (line.startsWith('el: if ') || line.startsWith('el:if ')) {
                const m = line.match(/^el:\s*if\s+(.+?):?\s*$/);
                if (m) {
                    if (this.blocks.length > 0) this.blocks.pop();
                    const ind = '  '.repeat(this.blocks.length);
                    this.output.push(ind + `} else if (${this.transpileExpr(m[1])}) {`);
                    this.blocks.push({ indent, type: 'else if' });
                    continue;
                }
            }

            if (line === 'el:') {
                if (this.blocks.length > 0) this.blocks.pop();
                const ind = '  '.repeat(this.blocks.length);
                this.output.push(ind + '} else {');
                this.blocks.push({ indent, type: 'else' });
                continue;
            }

            while (this.blocks.length > 0 && indent <= this.blocks[this.blocks.length - 1].indent) {
                const block = this.blocks.pop();
                const ind = '  '.repeat(this.blocks.length);
                this.output.push(ind + '}');
            }

            const ind = '  '.repeat(this.blocks.length);

            if (line.startsWith('class ')) {
                const m = line.match(/^class\s+(\w+):?\s*$/);
                if (m) {
                    this.output.push(ind + `class ${m[1]} {`);
                    this.blocks.push({ indent, type: 'class', className: m[1] });
                    continue;
                }
            }

            const inClass = this.blocks.some(b => b.type === 'class');

            if (line.startsWith('fn ') && inClass) {
                const m = line.match(/^fn\s+(\w+)\s*\((.*?)\):?\s*$/);
                if (m) {
                    let params = m[2];
                    let jsParams = params;
                    if (params.startsWith('self')) {
                        jsParams = params.split(',').slice(1).map(p => p.trim()).join(', ');
                    }
                    const name = m[1] === 'init' ? 'constructor' : m[1];
                    this.output.push(ind + `${name}(${jsParams}) {`);
                    this.blocks.push({ indent, type: 'fn' });
                    continue;
                }
            }

            if (line.startsWith('fn ')) {
                const m = line.match(/^fn\s+(\w+)\s*\((.*?)\):?\s*$/);
                if (m) {
                    this.output.push(ind + `function ${m[1]}(${m[2]}) {`);
                    this.blocks.push({ indent, type: 'fn' });
                    continue;
                }
            }

            if (line.startsWith('if ')) {
                const m = line.match(/^if\s+(.+?):?\s*$/);
                if (m) {
                    this.output.push(ind + `if (${this.transpileExpr(m[1])}) {`);
                    this.blocks.push({ indent, type: 'if' });
                    continue;
                }
            }

            if (line.startsWith('while ')) {
                const m = line.match(/^while\s+(.+?):?\s*$/);
                if (m) {
                    this.output.push(ind + `while (${this.transpileExpr(m[1])}) {`);
                    this.blocks.push({ indent, type: 'while' });
                    continue;
                }
            }

            if (line.startsWith('for ')) {
                const m = line.match(/^for\s+(\w+)\s+in\s+(.+?):?\s*$/);
                if (m) {
                    this.output.push(ind + `for (const ${m[1]} of ${this.transpileExpr(m[2])}) {`);
                    this.blocks.push({ indent, type: 'for' });
                    continue;
                }
            }

            if (line.startsWith('ret ')) {
                let val = line.slice(4).trim();
                if (val === 'self') val = 'this';
                this.output.push(ind + `return ${this.transpileExpr(val)};`);
                continue;
            }

            if (line === 'ret') {
                this.output.push(ind + 'return;');
                continue;
            }

            if (line.startsWith('let ')) {
                const m = line.match(/^let\s+(\w+)\s*=\s*(.+)$/);
                if (m) {
                    this.output.push(ind + `let ${m[1]} = ${this.transpileExpr(m[2])};`);
                    continue;
                }
            }

            if (line.startsWith('print(')) {
                const m = line.match(/^print\((.+)\)$/);
                if (m) {
                    this.output.push(ind + `console.log(${this.transpileExpr(m[1])});`);
                    continue;
                }
            }

            if (line === 'exit()') {
                this.output.push(ind + 'process.exit(0);');
                continue;
            }

            this.output.push(ind + this.transpileExpr(line) + ';');
        }

        while (this.blocks.length > 0) {
            this.blocks.pop();
            const ind = '  '.repeat(this.blocks.length);
            this.output.push(ind + '}');
        }

        return this.output.join('\n');
    }

    transpileExpr(expr) {
        expr = expr.trim();

        for (const cn of this.classNames) {
            const re = new RegExp(`\\b${cn}\\(`, 'g');
            expr = expr.replace(re, `new ${cn}(`);
        }

        if ((expr.startsWith('"') && expr.endsWith('"')) || (expr.startsWith("'") && expr.endsWith("'"))) {
            if (expr.startsWith("'")) {
                expr = '"' + expr.slice(1, -1).replace(/"/g, '\\"') + '"';
            }
            return expr;
        }

        if (/^\d+(\.\d+)?$/.test(expr)) return expr;
        if (expr === 'true') return 'true';
        if (expr === 'false') return 'false';
        if (expr === 'none') return 'null';
        if (expr === 'infinity') return 'Infinity';
        if (expr === 'pi') return 'Math.PI';

        expr = expr.replace(/\band\b/g, '&&');
        expr = expr.replace(/\bor\b/g, '||');
        expr = expr.replace(/\bnot\b/g, '!');
        expr = expr.replace(/\bself\./g, 'this.');

        expr = expr.replace(/\blen\(([^)]+)\)/g, (_, a) => `(${a}).length`);
        expr = expr.replace(/\bstr\(([^)]+)\)/g, (_, a) => `String(${a})`);
        expr = expr.replace(/\bint\(([^)]+)\)/g, (_, a) => `parseInt(${a})`);
        expr = expr.replace(/\bfloat\(([^)]+)\)/g, (_, a) => `parseFloat(${a})`);
        expr = expr.replace(/\babs\(([^)]+)\)/g, (_, a) => `Math.abs(${a})`);
        expr = expr.replace(/\bsqrt\(([^)]+)\)/g, (_, a) => `Math.sqrt(${a})`);
        expr = expr.replace(/\bexp\(([^)]+)\)/g, (_, a) => `Math.exp(${a})`);
        expr = expr.replace(/\blog\(([^)]+)\)/g, (_, a) => `Math.log(${a})`);
        expr = expr.replace(/\bpow\(([^,]+),\s*([^)]+)\)/g, (_, a, b) => `Math.pow(${a}, ${b})`);
        expr = expr.replace(/\bmax\(([^,]+),\s*([^)]+)\)/g, (_, a, b) => `Math.max(${a}, ${b})`);
        expr = expr.replace(/\bmin\(([^,]+),\s*([^)]+)\)/g, (_, a, b) => `Math.min(${a}, ${b})`);
        expr = expr.replace(/\bord\(([^)]+)\)/g, (_, a) => `${a}.charCodeAt(0)`);
        expr = expr.replace(/\brange\(([^)]+)\)/g, (_, a) => `Array.from({length: ${a}}, (_, i) => i)`);
        expr = expr.replace(/\.append\(([^)]+)\)/g, (_, a) => `.push(${a})`);
        expr = expr.replace(/\.remove\(([^)]+)\)/g, (_, a) => `.splice(${a}, 1)`);
        expr = expr.replace(/\.keys\(\)/g, '.keys()');
        expr = expr.replace(/\.values\(\)/g, '.values()');
        expr = expr.replace(/\.items\(\)/g, '.entries()');
        expr = expr.replace(/\.slice\(([^)]+)\)/g, (_, a) => `.slice(${a})`);

        return expr;
    }
}

if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.error('Usage: node zpx-to-js.js <input.zpx> [output.js]');
        process.exit(1);
    }
    const inputFile = args[0];
    const outputFile = args[1] || inputFile.replace('.zpx', '.js');
    const zapCode = fs.readFileSync(inputFile, 'utf-8');
    const transpiler = new ZapToJS();
    const jsCode = transpiler.transpile(zapCode);
    fs.writeFileSync(outputFile, jsCode);
    console.log(`Compiled ${inputFile} -> ${outputFile}`);
}

module.exports = ZapToJS;
