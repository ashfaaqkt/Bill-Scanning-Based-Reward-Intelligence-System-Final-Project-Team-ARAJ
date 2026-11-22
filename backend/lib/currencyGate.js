/**
 * Currency gate — refuses receipts in currencies the reward engine does not
 * price, BEFORE anything is written to Firestore or any reward is computed.
 *
 * Why a gate and not conversion: the points formula (₹100 = 1 pt), the anomaly
 * reference (POPULATION_REFERENCE_INR) and the offer catalogue are all INR. A
 * SAR 100 receipt scored by them would earn the points of a ₹100 one — about a
 * twenty-second of its value — and be judged against Indian spending. Refusing
 * is the honest behaviour until those parts are made currency-aware.
 *
 * ONE place configures it: SUPPORTED_CURRENCIES (comma-separated ISO 4217
 * codes) in the backend environment, defaulting to DEFAULT_SUPPORTED_CURRENCIES.
 * Widening the gate is a one-line change to either.
 */
const { normalizeCurrencyCode, parseAmount } = require('./currency');

const DEFAULT_SUPPORTED_CURRENCIES = ['INR'];

/** Read at call time, so a test or a restarted process sees the current env. */
function getSupportedCurrencies() {
    const raw = process.env.SUPPORTED_CURRENCIES;
    if (!raw || !raw.trim()) return [...DEFAULT_SUPPORTED_CURRENCIES];
    const codes = raw.split(',').map(c => c.trim().toUpperCase()).filter(c => /^[A-Z]{3}$/.test(c));
    return codes.length ? [...new Set(codes)] : [...DEFAULT_SUPPORTED_CURRENCIES];
}

/**
 * The receipt's currency as an ISO code, or null.
 * The extraction model's `currency` field wins when it is a valid code; else a
 * marker printed in the total (e.g. "₹ 299", "٢٩٩ ر.س") is used. Nothing here
 * defaults to INR — an unknown currency stays unknown.
 */
function resolveReceiptCurrency(receiptData) {
    const data = receiptData || {};
    return normalizeCurrencyCode(data.currency) || parseAmount(data.total).currency || null;
}

function supportedMessage(supported) {
    return `Only ${supported.join(', ')} receipts are supported.`;
}

/** { status, body } describing the refusal, or null if the currency is accepted. */
function currencyRejection(currency, supported = getSupportedCurrencies()) {
    if (!currency) {
        return {
            status: 422,
            body: {
                error: 'CURRENCY_NOT_DETECTED',
                message: `We could not tell which currency this receipt is in. ${supportedMessage(supported)}`,
                detectedCurrency: null,
                supportedCurrencies: supported,
            },
        };
    }
    if (!supported.includes(currency)) {
        return {
            status: 422,
            body: {
                error: 'UNSUPPORTED_CURRENCY',
                message: supportedMessage(supported),
                detectedCurrency: currency,
                supportedCurrencies: supported,
            },
        };
    }
    return null;
}

/**
 * Express middleware. Expects the extracted receipt on req.receiptData (set by
 * the OCR stage of /api/upload); records the resolved ISO code back onto it.
 */
function requireSupportedCurrency() {
    return function currencyGate(req, res, next) {
        const currency = resolveReceiptCurrency(req.receiptData);
        const rejection = currencyRejection(currency);
        if (rejection) {
            console.log(`[INFO] Upload refused at currency gate: ${rejection.body.error} (${currency})`);
            return res.status(rejection.status).json(rejection.body);
        }
        req.receiptData.currency = currency;
        return next();
    };
}

module.exports = {
    DEFAULT_SUPPORTED_CURRENCIES, getSupportedCurrencies, resolveReceiptCurrency,
    currencyRejection, requireSupportedCurrency,
};
