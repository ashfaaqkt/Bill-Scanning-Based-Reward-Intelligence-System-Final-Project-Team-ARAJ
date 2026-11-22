// Date normalisation — v1.0 formats must not regress; Arabic digits and months added.
const test = require('node:test');
const assert = require('node:assert/strict');
const { normalizeReceiptDate } = require('../lib/dates');

test('v1.0 formats are unchanged', () => {
    assert.equal(normalizeReceiptDate('2026-04-15'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15/04/2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15-04-2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('5/4/2026'), '2026-04-05', 'ambiguous → day-first');
    assert.equal(normalizeReceiptDate('15/04/26'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15/04/99'), '1999-04-15');
    assert.equal(normalizeReceiptDate('15 Apr 2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15 April 2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('Apr 15, 2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate(''), null);
    assert.equal(normalizeReceiptDate(null), null);
    assert.equal(normalizeReceiptDate('not a date'), null);
});

test('dd/mm vs mm/dd: unambiguous month-first is recognised, impossible dates refused', () => {
    assert.equal(normalizeReceiptDate('04/15/2026'), '2026-04-15', 'second field > 12 → mm/dd');
    assert.equal(normalizeReceiptDate('31/02/2026'), null, 'not a real date');
    assert.equal(normalizeReceiptDate('2026/04/15'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15.04.2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('15/04/2026 13:45'), '2026-04-15', 'trailing time ignored');
});

test('Eastern Arabic digits', () => {
    assert.equal(normalizeReceiptDate('١٥/٠٤/٢٠٢٦'), '2026-04-15');
    assert.equal(normalizeReceiptDate('٢٠٢٦-٠٤-١٥'), '2026-04-15');
    assert.equal(normalizeReceiptDate('‏١٥/٠٤/٢٠٢٦‏'), '2026-04-15', 'RTL marks stripped');
});

test('Arabic month names (Gulf/Egyptian and Levantine)', () => {
    assert.equal(normalizeReceiptDate('15 أبريل 2026'), '2026-04-15');
    assert.equal(normalizeReceiptDate('١٥ ابريل ٢٠٢٦'), '2026-04-15');
    assert.equal(normalizeReceiptDate('3 يناير 2026'), '2026-01-03');
    assert.equal(normalizeReceiptDate('٢١ ديسمبر ٢٠٢٥'), '2025-12-21');
    assert.equal(normalizeReceiptDate('10 أغسطس، 2026'), '2026-08-10');
    assert.equal(normalizeReceiptDate('7 نيسان 2026'), '2026-04-07');
    assert.equal(normalizeReceiptDate('1 تشرين الثاني 2026'), '2026-11-01');
    assert.equal(normalizeReceiptDate('1 كانون الأول 2026'), '2026-12-01');
    assert.equal(normalizeReceiptDate('15 أبريل 2026م'), '2026-04-15', 'Gregorian marker');
});

test('Hijri dates are refused rather than misread as Gregorian', () => {
    assert.equal(normalizeReceiptDate('١٤٤٧/١٠/٢٧ هـ'), null);
    assert.equal(normalizeReceiptDate('27/10/1447'), null);
});
