/**
 * Receipt date normalisation → ISO yyyy-mm-dd, or null.
 *
 * DAY/MONTH RULE (numeric dates such as 05/04/2026):
 *   1. If the first field is > 12 it must be the day            (15/04 → 15 Apr)
 *   2. else if the second field is > 12 it must be the day       (04/15 → 15 Apr)
 *   3. else the date is genuinely ambiguous and is read DAY-FIRST (05/04 → 5 Apr)
 * Day-first is the convention in India and across the Gulf, the markets this
 * system serves, and it is what v1.0 always did. Rule 2 only rescues dates
 * v1.0 turned into impossible months ("2026-15-04").
 *
 * The result is calendar-checked: 31/02/2026 returns null rather than an
 * invalid ISO string. Years before 1900 return null, which is what a Hijri date
 * (e.g. 1447 AH) would otherwise be silently misread as. Hijri calendars are
 * not converted — that needs a calendar library and is out of scope.
 */
const { toLatinDigits } = require('./currency');

const EN_MONTHS = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8,
    sep: 9, oct: 10, nov: 11, dec: 12 };

// Arabic month names after normaliseArabic() (alef variants folded to ا).
// Gulf/Egyptian transliterations first, then the Levantine/Iraqi names.
// Two-word names are listed so they match before their one-word prefixes.
const AR_MONTHS = [
    ['كانون الثاني', 1], ['كانون الاول', 12], ['تشرين الاول', 10], ['تشرين الثاني', 11],
    ['يناير', 1], ['فبراير', 2], ['مارس', 3], ['ابريل', 4], ['مايو', 5], ['يونيو', 6],
    ['يوليو', 7], ['اغسطس', 8], ['سبتمبر', 9], ['اكتوبر', 10], ['نوفمبر', 11], ['ديسمبر', 12],
    ['شباط', 2], ['اذار', 3], ['نيسان', 4], ['ايار', 5], ['حزيران', 6], ['تموز', 7],
    ['اب', 8], ['ايلول', 9],
];

function normaliseArabic(s) {
    return s.replace(/[أإآ]/g, 'ا').replace(/ـ/g, '');
}

function isoIfValid(y, m, d) {
    if (y < 1900 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) return null;
    const dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
    return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function expandYear(y) {
    if (y.length === 2) return parseInt(y, 10) > 50 ? 1900 + parseInt(y, 10) : 2000 + parseInt(y, 10);
    return parseInt(y, 10);
}

function monthFromText(text) {
    const ar = normaliseArabic(text).trim();
    for (const [name, m] of AR_MONTHS) {
        // whole-word match: "اب" must not fire inside another word
        if (new RegExp(`(^|\\s)${name}(\\s|$)`).test(ar)) return m;
    }
    const en = text.match(/[a-zA-Z]{3,}/);
    if (en) return EN_MONTHS[en[0].slice(0, 3).toLowerCase()] || null;
    return null;
}

function normalizeReceiptDate(dateStr) {
    if (dateStr === null || dateStr === undefined) return null;
    let s = toLatinDigits(String(dateStr))
        .replace(/[‎‏؜‪-‮]/g, '')   // bidi marks
        .replace(/،/g, ',')
        .trim();
    if (!s) return null;

    // A Hijri marker means the numbers are not Gregorian. Refuse, don't guess.
    if (/هـ|\bAH\b/.test(s)) return null;
    s = s.replace(/(\d)\s*م(?=[\s,]|$)/g, '$1');   // Gregorian "م" suffix

    // Drop a trailing time, "15/04/2026 13:45", "... 1:05 PM", "... ٠١:٠٥ م".
    s = s.replace(/[\sT]+\d{1,2}:\d{2}(:\d{2})?(\.\d+)?\s*(am|pm|ص|م|z|[+-]\d{2}:?\d{2})?$/i, '').trim();

    // yyyy-mm-dd, yyyy/mm/dd, yyyy.mm.dd
    let m = s.match(/^(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})$/);
    if (m) return isoIfValid(+m[1], +m[2], +m[3]);

    // a/b/yyyy or a/b/yy, separators / - .
    m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2}|\d{4})$/);
    if (m) {
        const a = +m[1], b = +m[2], y = expandYear(m[3]);
        if (a > 12) return isoIfValid(y, b, a);
        if (b > 12) return isoIfValid(y, a, b);
        return isoIfValid(y, b, a);          // ambiguous → day-first
    }

    // Day, month name, year in either order of day/month: "15 Apr 2026",
    // "Apr 15, 2026", "١٥ أبريل ٢٠٢٦", "1 تشرين الثاني 2026".
    const year = s.match(/(^|\D)(\d{4})(\D|$)/);
    if (year) {
        const rest = s.replace(year[2], ' ');
        const day = rest.match(/(^|\D)(\d{1,2})(st|nd|rd|th)?(\D|$)/i);
        const month = monthFromText(rest.replace(/\d+(st|nd|rd|th)?/gi, ' ').replace(/[,.\-\/]/g, ' '));
        if (day && month) return isoIfValid(+year[2], month, +day[2]);
    }

    // Last resort, as in v1.0: the platform parser, Latin text only.
    if (!/[؀-ۿ]/.test(s)) {
        const parsed = new Date(s);
        if (!isNaN(parsed.getTime())) {
            return isoIfValid(parsed.getFullYear(), parsed.getMonth() + 1, parsed.getDate());
        }
    }
    return null;
}

module.exports = { normalizeReceiptDate };
