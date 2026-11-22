/**
 * Currency parsing for receipt amounts.
 *
 * v1.0 stripped a fixed list of INR-style symbols and every comma, then called
 * parseFloat. That silently assumed INR and Latin digits: "١٢٣٫٥٠ ر.س" parsed
 * to 0, and "1.234,50" (European grouping) parsed to 1.2345. This module
 * returns the amount AND the currency it saw, and never fills in INR when no
 * marker is present — deciding what to do with an unknown currency is the
 * currency gate's job (lib/currencyGate.js), not the parser's.
 */

// Eastern Arabic (U+0660–0669) and Extended Arabic-Indic / Persian (U+06F0–06F9).
const ARABIC_ZERO = 0x0660;
const PERSIAN_ZERO = 0x06F0;
const ARABIC_DECIMAL_SEPARATOR = '٫';   // ٫
const ARABIC_THOUSANDS_SEPARATOR = '٬'; // ٬

function toLatinDigits(value) {
    return String(value).replace(/[٠-٩۰-۹]/g, ch => {
        const code = ch.charCodeAt(0);
        return String(code >= PERSIAN_ZERO ? code - PERSIAN_ZERO : code - ARABIC_ZERO);
    });
}

// ISO 4217 codes this system knows how to recognise. Recognising a currency is
// not the same as supporting it — see SUPPORTED_CURRENCIES in lib/currencyGate.js.
const KNOWN_CODES = new Set(['INR', 'SAR', 'AED', 'QAR', 'USD', 'KWD', 'BHD', 'OMR',
    'EUR', 'GBP', 'MYR', 'IDR']);

// Markers as they appear printed on receipts. Order matters only for
// readability; detection collects every match and refuses if they disagree.
// Arabic abbreviations are written with or without the dot and with optional
// spacing ("ر.س", "ر س", "رس").
const CURRENCY_PATTERNS = [
    ['INR', /₹|\bINR\b|\bRs\.?(?=\s|\d|$)|रु/i],
    ['SAR', /ر\s?\.?\s?س|\bSAR\b|\bSR\b/i],
    ['AED', /د\s?\.?\s?إ|\bAED\b|\bDhs?\b\.?/i],
    ['QAR', /ر\s?\.?\s?ق|\bQAR\b|\bQR\b/i],
    ['USD', /US\$|\$|\bUSD\b/i],
    ['EUR', /€|\bEUR\b/i],
    ['GBP', /£|\bGBP\b/i],
];

/**
 * The single currency marked in `text`, or null if there is none or if two
 * different currencies are marked (ambiguous — better unknown than wrong).
 * A bare "$" is read as USD; no supported market prints another dollar.
 */
function detectCurrency(text) {
    if (text === null || text === undefined) return null;
    const s = String(text);
    const found = new Set();
    for (const [code, pattern] of CURRENCY_PATTERNS) {
        if (pattern.test(s)) found.add(code);
    }
    return found.size === 1 ? [...found][0] : null;
}

/** ISO code for a model-supplied currency field ("sar", "₹", "ر.س"), or null. */
function normalizeCurrencyCode(value) {
    if (value === null || value === undefined) return null;
    const s = String(value).trim();
    if (!s) return null;
    const upper = s.toUpperCase();
    if (/^[A-Z]{3}$/.test(upper)) return KNOWN_CODES.has(upper) ? upper : null;
    return detectCurrency(s);
}

function stripCurrencyMarkers(s) {
    let out = s;
    for (const [, pattern] of CURRENCY_PATTERNS) {
        out = out.replace(new RegExp(pattern.source, pattern.flags.includes('g') ? pattern.flags : pattern.flags + 'g'), ' ');
    }
    return out;
}

/**
 * Turn the digit run of an amount into a number, deciding which separator is
 * the decimal one:
 *   - ٫ is always decimal, ٬ always grouping (Arabic typography).
 *   - Both "," and "." present → whichever comes LAST is the decimal separator
 *     (1,234.50 and 1.234,50 are both 1234.5).
 *   - Only commas → grouping if the final group has exactly three digits
 *     (1,234 · 1,23,456 Indian lakh), else a single comma is decimal (12,5).
 *   - Only dots → several dots are grouping (1.234.567); a single dot is
 *     decimal. Every currency in scope has two minor digits, so "1.234" is read
 *     as one-point-two-three-four, matching v1.0. Three-decimal currencies
 *     (KWD, BHD, OMR) would need this rule revisited.
 */
function parseNumber(raw) {
    let s = raw.replace(new RegExp(ARABIC_THOUSANDS_SEPARATOR, 'g'), '')
        .replace(new RegExp(ARABIC_DECIMAL_SEPARATOR, 'g'), '.')
        .replace(/[\s  ']/g, '');
    const match = s.match(/-?\d[\d.,]*/);
    if (!match) return null;
    s = match[0].replace(/[.,]+$/, '');

    const lastComma = s.lastIndexOf(',');
    const lastDot = s.lastIndexOf('.');
    if (lastComma !== -1 && lastDot !== -1) {
        if (lastComma > lastDot) s = s.replace(/\./g, '').replace(',', '.');
        else s = s.replace(/,/g, '');
    } else if (lastComma !== -1) {
        const groups = s.split(',');
        const last = groups[groups.length - 1];
        if (groups.length === 2 && last.length !== 3) s = s.replace(',', '.');
        else s = s.replace(/,/g, '');
    } else if ((s.match(/\./g) || []).length > 1) {
        s = s.replace(/\./g, '');
    }
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : null;
}

/**
 * Parse a receipt amount. Returns { amount, currency }:
 *   amount   — number, or null when there are no digits
 *   currency — ISO code from a printed marker, or null. Never defaults to INR.
 * A plain number is returned as-is with currency null.
 */
function parseAmount(value) {
    if (value === null || value === undefined) return { amount: null, currency: null };
    if (typeof value === 'number') {
        return { amount: Number.isFinite(value) ? value : null, currency: null };
    }
    const latin = toLatinDigits(String(value));
    const currency = detectCurrency(latin);
    const amount = parseNumber(stripCurrencyMarkers(latin));
    return { amount, currency };
}

/**
 * v1.0 contract, kept for every existing caller: a number out, 0 when nothing
 * parses. Use parseAmount when the currency matters.
 */
function sanitizeCurrencyValue(value) {
    const { amount } = parseAmount(value);
    return amount === null ? 0 : amount;
}

module.exports = {
    toLatinDigits, detectCurrency, normalizeCurrencyCode, parseAmount, sanitizeCurrencyValue,
    KNOWN_CODES,
};
