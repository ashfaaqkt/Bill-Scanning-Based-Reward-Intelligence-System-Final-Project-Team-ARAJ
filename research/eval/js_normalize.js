#!/usr/bin/env node
/**
 * Runs a code root's OWN backend post-processing on extracted receipts.
 *
 *   node research/eval/js_normalize.js <code_root>   < in.jsonl   > out.jsonl
 *
 * Each input line is an extraction result ({ total, date, currency, ... }).
 * Each output line is { amount, date_iso, currency, gate_status, gate_error }.
 *
 * For a root with backend/lib (this branch, main after v1.1) the modules are
 * required directly. For v1.0-fyp, where the helpers were private functions in
 * server.js, their exact source text is cut out of that file and evaluated in
 * an isolated context. Nothing is reimplemented, so the BEFORE numbers come
 * from the v1.0 code itself.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const readline = require('readline');

const root = path.resolve(process.argv[2] || '.');
const lib = path.join(root, 'backend', 'lib');

function cutFunction(source, name) {
    const start = source.indexOf(`function ${name}(`);
    if (start === -1) throw new Error(`${name} not found in server.js`);
    let depth = 0, i = source.indexOf('{', start);
    for (; i < source.length; i++) {
        if (source[i] === '{') depth++;
        else if (source[i] === '}' && --depth === 0) break;
    }
    return source.slice(start, i + 1);
}

let api;
if (fs.existsSync(path.join(lib, 'currency.js'))) {
    const currency = require(path.join(lib, 'currency.js'));
    const { normalizeReceiptDate } = require(path.join(lib, 'dates.js'));
    const gate = require(path.join(lib, 'currencyGate.js'));
    api = {
        version: 'v1.1+',
        amount: v => currency.parseAmount(v).amount,
        date: normalizeReceiptDate,
        currency: r => gate.resolveReceiptCurrency(r),
        gate: c => gate.currencyRejection(c),
    };
} else {
    const src = fs.readFileSync(path.join(root, 'backend', 'server.js'), 'utf8');
    const ctx = vm.createContext({});
    vm.runInContext(cutFunction(src, 'normalizeReceiptDate') + '\n'
        + cutFunction(src, 'sanitizeCurrencyValue'), ctx);
    api = {
        version: 'v1.0',
        amount: v => ctx.sanitizeCurrencyValue(v),
        date: v => ctx.normalizeReceiptDate(v),
        // v1.0 had no currency concept: every receipt was priced as INR.
        currency: () => 'INR',
        gate: () => null,
    };
}

const rl = readline.createInterface({ input: process.stdin });
rl.on('line', line => {
    if (!line.trim()) return;
    const r = JSON.parse(line);
    const out = { amount: null, date_iso: null, currency: null, gate_status: null, gate_error: null,
        normaliser: api.version };
    if (r.error) {
        out.gate_status = 'rejected_ocr';
        out.gate_error = r.error;
    } else {
        // Same order as the route: currency gate (v1.1+) → amount → date.
        out.currency = api.currency(r);
        const rejection = api.gate(out.currency);
        out.amount = r.total === undefined ? null : api.amount(r.total);
        out.date_iso = api.date(r.date) || null;
        if (rejection) {
            out.gate_status = 'rejected_currency';
            out.gate_error = rejection.body.error;
        } else if (!out.amount || out.amount <= 0) {
            out.gate_status = 'rejected_fields';
            out.gate_error = 'invalid or missing total amount';
        } else if (!out.date_iso) {
            out.gate_status = 'rejected_fields';
            out.gate_error = 'could not parse date';
        } else {
            out.gate_status = 'accepted';
        }
    }
    process.stdout.write(JSON.stringify(out) + '\n');
});
