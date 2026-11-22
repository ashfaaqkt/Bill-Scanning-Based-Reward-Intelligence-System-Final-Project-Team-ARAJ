// Currency parsing — Eastern Arabic digits, Gulf symbols, separator conventions.
// Run: cd backend && npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const {
    toLatinDigits, detectCurrency, normalizeCurrencyCode, parseAmount, sanitizeCurrencyValue,
} = require('../lib/currency');

test('toLatinDigits converts Eastern Arabic and Persian digits', () => {
    assert.equal(toLatinDigits('٠١٢٣٤٥٦٧٨٩'), '0123456789');
    assert.equal(toLatinDigits('۰۱۲۳۴۵۶۷۸۹'), '0123456789');
    assert.equal(toLatinDigits('abc 12'), 'abc 12');
});

test('normalizeCurrencyCode accepts ISO codes and common aliases, rejects junk', () => {
    assert.equal(normalizeCurrencyCode('inr'), 'INR');
    assert.equal(normalizeCurrencyCode(' SAR '), 'SAR');
    assert.equal(normalizeCurrencyCode('₹'), 'INR');
    assert.equal(normalizeCurrencyCode('Rs.'), 'INR');
    assert.equal(normalizeCurrencyCode('ر.س'), 'SAR');
    assert.equal(normalizeCurrencyCode('د.إ'), 'AED');
    assert.equal(normalizeCurrencyCode('ر.ق'), 'QAR');
    assert.equal(normalizeCurrencyCode('$'), 'USD');
    assert.equal(normalizeCurrencyCode(null), null);
    assert.equal(normalizeCurrencyCode(''), null);
    assert.equal(normalizeCurrencyCode('unknown'), null);
    assert.equal(normalizeCurrencyCode('XYZ'), null);
});

test('detectCurrency finds the currency marker in free text', () => {
    assert.equal(detectCurrency('₹ 1,234.50'), 'INR');
    assert.equal(detectCurrency('Rs. 299'), 'INR');
    assert.equal(detectCurrency('INR 500'), 'INR');
    assert.equal(detectCurrency('١٢٣٫٥٠ ر.س'), 'SAR');
    assert.equal(detectCurrency('SAR 45.00'), 'SAR');
    assert.equal(detectCurrency('د.إ 99'), 'AED');
    assert.equal(detectCurrency('AED 99'), 'AED');
    assert.equal(detectCurrency('ر.ق 12'), 'QAR');
    assert.equal(detectCurrency('QAR 12'), 'QAR');
    assert.equal(detectCurrency('$19.99'), 'USD');
    assert.equal(detectCurrency('1,234.50'), null);
    assert.equal(detectCurrency('SAR 10 / AED 10'), null, 'two different markers is ambiguous');
});

test('parseAmount returns amount AND currency, never assuming INR', () => {
    assert.deepEqual(parseAmount('₹1,234.50'), { amount: 1234.5, currency: 'INR' });
    assert.deepEqual(parseAmount('Rs. 299'), { amount: 299, currency: 'INR' });
    assert.deepEqual(parseAmount('1,234.50'), { amount: 1234.5, currency: null });
    assert.deepEqual(parseAmount(1234.5), { amount: 1234.5, currency: null });
    assert.deepEqual(parseAmount('SAR 1.234,50'), { amount: 1234.5, currency: 'SAR' });
    assert.deepEqual(parseAmount('١٬٢٣٤٫٥٠ ر.س'), { amount: 1234.5, currency: 'SAR' });
    assert.deepEqual(parseAmount('٤٥٫٠٠ د.إ'), { amount: 45, currency: 'AED' });
    assert.deepEqual(parseAmount('QAR ٧٨'), { amount: 78, currency: 'QAR' });
    assert.deepEqual(parseAmount('$19.99'), { amount: 19.99, currency: 'USD' });
    assert.deepEqual(parseAmount('1,23,456.00'), { amount: 123456, currency: null }, 'Indian lakh grouping');
    assert.deepEqual(parseAmount('12,5'), { amount: 12.5, currency: null }, 'decimal comma');
    assert.deepEqual(parseAmount('1.234.567'), { amount: 1234567, currency: null });
    assert.deepEqual(parseAmount('no digits here'), { amount: null, currency: null });
    assert.deepEqual(parseAmount(null), { amount: null, currency: null });
});

test('sanitizeCurrencyValue keeps its v1.0 contract (number out, 0 on failure)', () => {
    assert.equal(sanitizeCurrencyValue(299), 299);
    assert.equal(sanitizeCurrencyValue('₹ 1,234.50'), 1234.5);
    assert.equal(sanitizeCurrencyValue('Rs.299'), 299);
    assert.equal(sanitizeCurrencyValue('INR 2,748'), 2748);
    assert.equal(sanitizeCurrencyValue('€12'), 12);
    assert.equal(sanitizeCurrencyValue('abc'), 0);
    assert.equal(sanitizeCurrencyValue(''), 0);
});
