// Currency gate — unit tests for the middleware, and an end-to-end test of
// POST /api/upload against a stub ML service and a spied Firestore handle, to
// prove a rejected receipt reaches neither the database nor the reward engine.
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');

const {
    DEFAULT_SUPPORTED_CURRENCIES, getSupportedCurrencies, resolveReceiptCurrency,
    requireSupportedCurrency,
} = require('../lib/currencyGate');

// ── unit ─────────────────────────────────────────────────────────────────────
function runGate(receiptData, env) {
    const saved = process.env.SUPPORTED_CURRENCIES;
    if (env === undefined) delete process.env.SUPPORTED_CURRENCIES;
    else process.env.SUPPORTED_CURRENCIES = env;
    try {
        const req = { receiptData };
        const out = { status: null, body: null, nextCalled: false };
        const res = {
            status(code) { out.status = code; return this; },
            json(body) { out.body = body; return this; },
        };
        requireSupportedCurrency()(req, res, () => { out.nextCalled = true; });
        return { ...out, req };
    } finally {
        if (saved === undefined) delete process.env.SUPPORTED_CURRENCIES;
        else process.env.SUPPORTED_CURRENCIES = saved;
    }
}

test('default supported list is exactly ["INR"]', () => {
    assert.deepEqual(DEFAULT_SUPPORTED_CURRENCIES, ['INR']);
    const saved = process.env.SUPPORTED_CURRENCIES;
    delete process.env.SUPPORTED_CURRENCIES;
    assert.deepEqual(getSupportedCurrencies(), ['INR']);
    process.env.SUPPORTED_CURRENCIES = 'inr, sar ,AED';
    assert.deepEqual(getSupportedCurrencies(), ['INR', 'SAR', 'AED']);
    process.env.SUPPORTED_CURRENCIES = '   ';
    assert.deepEqual(getSupportedCurrencies(), ['INR'], 'blank falls back to default');
    if (saved === undefined) delete process.env.SUPPORTED_CURRENCIES; else process.env.SUPPORTED_CURRENCIES = saved;
});

test('resolveReceiptCurrency prefers the model field, falls back to the total string', () => {
    assert.equal(resolveReceiptCurrency({ currency: 'sar', total: 10 }), 'SAR');
    assert.equal(resolveReceiptCurrency({ currency: null, total: '₹ 299' }), 'INR');
    assert.equal(resolveReceiptCurrency({ currency: 'garbage', total: 'AED 5' }), 'AED');
    assert.equal(resolveReceiptCurrency({ total: 299 }), null);
});

test('INR passes the gate and the currency is recorded on the receipt', () => {
    const r = runGate({ currency: 'INR', total: 299 });
    assert.equal(r.nextCalled, true);
    assert.equal(r.status, null);
    assert.equal(r.req.receiptData.currency, 'INR');
});

for (const code of ['SAR', 'AED', 'QAR', 'USD']) {
    test(`${code} is rejected with 422 UNSUPPORTED_CURRENCY`, () => {
        const r = runGate({ currency: code, total: 10 });
        assert.equal(r.nextCalled, false);
        assert.equal(r.status, 422);
        assert.deepEqual(r.body, {
            error: 'UNSUPPORTED_CURRENCY',
            message: 'Only INR receipts are supported.',
            detectedCurrency: code,
            supportedCurrencies: ['INR'],
        });
    });
}

test('missing currency is rejected with 422 CURRENCY_NOT_DETECTED', () => {
    const r = runGate({ currency: null, total: 299 });
    assert.equal(r.nextCalled, false);
    assert.equal(r.status, 422);
    assert.equal(r.body.error, 'CURRENCY_NOT_DETECTED');
    assert.equal(r.body.detectedCurrency, null);
    assert.deepEqual(r.body.supportedCurrencies, ['INR']);
    assert.equal(typeof r.body.message, 'string');
});

test('widening SUPPORTED_CURRENCIES admits SAR without code changes', () => {
    const r = runGate({ currency: 'SAR', total: 10 }, 'INR,SAR');
    assert.equal(r.nextCalled, true);
});

// ── end to end through /api/upload ───────────────────────────────────────────
const ocrReply = { current: null };
const mlCalls = [];
const mlServer = http.createServer((req, res) => {
    let body = '';
    req.on('data', c => { body += c; });
    req.on('end', () => {
        mlCalls.push(req.url);
        res.setHeader('Content-Type', 'application/json');
        if (req.url === '/ml/ocr') return res.end(JSON.stringify(ocrReply.current));
        if (req.url === '/ml/classify') return res.end(JSON.stringify({ model_ready: false }));
        return res.end(JSON.stringify({}));
    });
});

let server, baseUrl, db, token, firestoreTouches;
// A 1x1 PNG — passes the backend's magic-byte check.
const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

test.before(async () => {
    await new Promise(r => mlServer.listen(0, '127.0.0.1', r));
    process.env.ML_SERVICE_URL = `http://127.0.0.1:${mlServer.address().port}`;
    process.env.NODE_ENV = 'test';
    delete process.env.SUPPORTED_CURRENCIES;
    const mod = require('../server');
    db = mod.db;
    firestoreTouches = [];
    // Any Firestore use at all is recorded and then fails loudly. A rejected
    // upload must record nothing; an accepted one must get as far as this.
    for (const method of ['collection', 'batch', 'runTransaction', 'doc', 'collectionGroup']) {
        db[method] = (...args) => {
            firestoreTouches.push(method);
            throw new Error(`firestore.${method} called in test`);
        };
    }
    token = require('jsonwebtoken').sign({ userId: 'test-user' }, mod.JWT_SECRET);
    server = mod.app.listen(0, '127.0.0.1');
    await new Promise(r => server.once('listening', r));
    baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.after(async () => {
    await new Promise(r => server.close(r));
    await new Promise(r => mlServer.close(r));
});

async function upload(ocrResult) {
    ocrReply.current = ocrResult;
    firestoreTouches.length = 0;
    mlCalls.length = 0;
    const res = await fetch(`${baseUrl}/api/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ receipt: PNG_B64, mimeType: 'image/png' }),
    });
    return { status: res.status, body: await res.json() };
}

const receipt = (extra) => ({
    rawMerchant: 'Test Mart', date: '2026-04-15', total: 299,
    category: 'General Retail', items: [{ name: 'Soap', price: 299 }],
    handwritten_flag: false, handwritten_details: null, ...extra,
});

for (const code of ['SAR', 'AED', 'QAR', 'USD']) {
    test(`upload of a ${code} receipt → 422, no Firestore access, no ML scoring`, async () => {
        const { status, body } = await upload(receipt({ currency: code }));
        assert.equal(status, 422);
        assert.equal(body.error, 'UNSUPPORTED_CURRENCY');
        assert.equal(body.detectedCurrency, code);
        assert.deepEqual(firestoreTouches, []);
        assert.deepEqual(mlCalls, ['/ml/ocr'], 'no classify/fraud/profile/recommend call');
    });
}

test('upload with no detectable currency → 422 CURRENCY_NOT_DETECTED, no Firestore access', async () => {
    const { status, body } = await upload(receipt({ currency: null }));
    assert.equal(status, 422);
    assert.equal(body.error, 'CURRENCY_NOT_DETECTED');
    assert.deepEqual(firestoreTouches, []);
});

test('Arabic-digit SAR total string is detected and rejected', async () => {
    const { status, body } = await upload(receipt({ currency: undefined, total: '٢٩٩٫٠٠ ر.س' }));
    assert.equal(status, 422);
    assert.equal(body.detectedCurrency, 'SAR');
    assert.deepEqual(firestoreTouches, []);
});

test('INR receipt passes the gate and continues into the pipeline', async () => {
    const { status } = await upload(receipt({ currency: 'INR' }));
    // The spied Firestore throws on first use, so the route ends in its own
    // 500 handler — reaching Firestore at all is the proof the gate let it by.
    assert.equal(status, 500);
    assert.ok(firestoreTouches.length > 0, 'pipeline reached Firestore');
    assert.ok(mlCalls.includes('/ml/classify'));
});
