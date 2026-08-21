/**
 * Backend Server — Team ARAJ (Ashfaaq Feroz)
 * Node.js / Express REST API connecting the frontend, Firestore, Gemini AI, and ML microservice.
 * Handles auth, receipt OCR pipeline, reward calculation, fraud scoring, and analytics.
 */

// ── DEPENDENCIES ───────────────────────────────────────────────
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const express = require('express');
const cors = require('cors');
const axios = require('axios');          // HTTP client for calling ML microservice
const jwt = require('jsonwebtoken');     // JWT creation and verification
const bcrypt = require('bcrypt');        // Password hashing (salt rounds = 10)
const admin = require('firebase-admin');            // Firestore database access

// ── CONSTANTS ──────────────────────────────────────────────────
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5001';  // Python Flask ML service
// Below this the classifier's answer is discarded and Gemini's reading stands.
//
// Was 0.45, which was assumed rather than measured. On the 216-row test set the
// classifier is 94.4% accurate overall, but that average hides the low end:
//
//   0.45-0.55   n=4     50.0%   <- a coin flip on three classes
//   0.55-0.65   n=12    66.7%
//   0.65-0.75   n=22    90.9%
//   0.75+       n=176   ~99%
//
// A D'Mart bill (Receipt 96) came back General Retail at 0.5219 and overrode
// Gemini, which had correctly read Supermarket / Grocery from the merchant name
// and the image. Letting a coin flip beat the model that can see the receipt is
// the wrong way round, and the gate exists precisely to prevent it.
//
// At 0.65 the classifier keeps 198 of 216 predictions at 98.0% accuracy, and the
// 18 it gives up were right only 61% of the time. Re-measure with
// ml-service/train_classifier.py's test split if the model is ever retrained.
const CLASSIFIER_MIN_CONFIDENCE = 0.65;
// How many recent receipts to compare a new upload against perceptually. Every
// hash is sent to the ML service on each scan, so this trades duplicate recall
// against payload size; at this project's data volume it covers the whole corpus.
const PHASH_LOOKBACK = 300;
const SERVICE_ACCOUNT_PATH = path.join(__dirname, 'serviceAccountKey.json');
const SUPPORTED_IMAGE_MIME_TYPES = new Set([  // Receipt image formats accepted at upload
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif'
]);

// ── FIREBASE INITIALISATION ────────────────────────────────────
// Connects to live Firestore using serviceAccountKey.json or env credentials (CI/cloud)
function initializeFirebaseAdmin() {
    if (admin.apps.length > 0) return;

    if (process.env.GOOGLE_APPLICATION_CREDENTIALS || process.env.FIREBASE_CONFIG) {
        admin.initializeApp();
        console.log("✅ Firebase Admin initialized using environment credentials.");
        return;
    }

    if (!fs.existsSync(SERVICE_ACCOUNT_PATH)) {
        console.error("❌ Firebase credentials missing. Add serviceAccountKey.json in project root or set GOOGLE_APPLICATION_CREDENTIALS.");
        process.exit(1);
    }

    const serviceAccount = require(SERVICE_ACCOUNT_PATH);
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount)
    });
    console.log("✅ Authenticated securely with Live Firebase Firestore.");
}

// ── UTILITY HELPERS ────────────────────────────────────────────

// Trims and lowercases email for consistent Firestore queries
function normalizeEmail(email) {
    return String(email || '').trim().toLowerCase();
}

// ── MERCHANT FUZZY MATCHING (Ranjeet Singh) ───────────────────
// Used for fuzzy duplicate detection — catches typos and spacing variants

function normalizeMerchantName(name) {
    return String(name || '')
        .toLowerCase()
        .replace(/&/g, ' and ')
        .replace(/[^a-z0-9]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

function levenshteinDistance(a, b) {
    const left = String(a || '');
    const right = String(b || '');

    if (left === right) return 0;
    if (!left.length) return right.length;
    if (!right.length) return left.length;

    const prev = new Array(right.length + 1);
    const curr = new Array(right.length + 1);

    for (let j = 0; j <= right.length; j += 1) prev[j] = j;

    for (let i = 1; i <= left.length; i += 1) {
        curr[0] = i;
        for (let j = 1; j <= right.length; j += 1) {
            const cost = left[i - 1] === right[j - 1] ? 0 : 1;
            curr[j] = Math.min(
                prev[j] + 1,        // deletion
                curr[j - 1] + 1,    // insertion
                prev[j - 1] + cost  // substitution
            );
        }
        for (let j = 0; j <= right.length; j += 1) prev[j] = curr[j];
    }
    return prev[right.length];
}

function jaccardTokenSimilarity(a, b) {
    const leftTokens = new Set(String(a || '').split(' ').filter(Boolean));
    const rightTokens = new Set(String(b || '').split(' ').filter(Boolean));

    if (leftTokens.size === 0 || rightTokens.size === 0) return 0;

    let intersection = 0;
    for (const token of leftTokens) {
        if (rightTokens.has(token)) intersection += 1;
    }
    const union = leftTokens.size + rightTokens.size - intersection;
    return union === 0 ? 0 : (intersection / union);
}

function merchantSimilarityScore(merchantA, merchantB) {
    const left = normalizeMerchantName(merchantA);
    const right = normalizeMerchantName(merchantB);
    if (!left || !right) return 0;
    if (left === right) return 1;

    const editDistance = levenshteinDistance(left, right);
    const maxLen = Math.max(left.length, right.length) || 1;
    const editSimilarity = 1 - (editDistance / maxLen);
    const tokenSimilarity = jaccardTokenSimilarity(left, right);
    return Math.max(editSimilarity, tokenSimilarity);
}

// Validates a base64 string (used to reject malformed image payloads)
function isValidBase64String(value) {
    return typeof value === 'string'
        && value.length > 0
        && value.length % 4 === 0
        && /^[A-Za-z0-9+/]+={0,2}$/.test(value);
}

// Checks magic bytes in the image buffer to confirm mimeType matches actual file content
function looksLikeExpectedImageType(imageBuffer, mimeType) {
    if (mimeType === 'image/jpeg' || mimeType === 'image/jpg') {
        return imageBuffer.length > 3
            && imageBuffer[0] === 0xFF
            && imageBuffer[1] === 0xD8
            && imageBuffer[2] === 0xFF;
    }

    if (mimeType === 'image/png') {
        const pngSig = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
        return imageBuffer.length >= pngSig.length
            && pngSig.every((byte, idx) => imageBuffer[idx] === byte);
    }

    if (mimeType === 'image/webp') {
        return imageBuffer.length > 12
            && imageBuffer.subarray(0, 4).toString('ascii') === 'RIFF'
            && imageBuffer.subarray(8, 12).toString('ascii') === 'WEBP';
    }

    if (mimeType === 'image/heic' || mimeType === 'image/heif') {
        if (imageBuffer.length < 16) return false;
        const box = imageBuffer.subarray(4, 16).toString('ascii').toLowerCase();
        return box.startsWith('ftypheic')
            || box.startsWith('ftypheif')
            || box.startsWith('ftypmif1')
            || box.startsWith('ftypmsf1');
    }

    return false;
}

/**
 * Normalizes various Indian receipt date formats to YYYY-MM-DD.
 * Handles: DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, "15 Apr 2026", "Apr 15, 2026", ISO.
 */
function normalizeReceiptDate(dateStr) {
    if (!dateStr) return null;
    const s = String(dateStr).trim();

    // Already YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;

    // DD/MM/YYYY or DD-MM-YYYY
    const dmy = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (dmy) {
        const [, d, m, y] = dmy;
        return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // DD/MM/YY or DD-MM-YY
    const dmyShort = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})$/);
    if (dmyShort) {
        const [, d, m, y] = dmyShort;
        const fullYear = parseInt(y) > 50 ? `19${y}` : `20${y}`;
        return `${fullYear}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // DD MMM YYYY (e.g. "15 Apr 2026")
    const MONTHS = { jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12 };
    const dmyText = s.match(/^(\d{1,2})\s+([a-zA-Z]{3,})\s+(\d{4})$/);
    if (dmyText) {
        const [, d, mon, y] = dmyText;
        const m = MONTHS[mon.slice(0, 3).toLowerCase()];
        if (m) return `${y}-${String(m).padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // MMM DD, YYYY (e.g. "Apr 15, 2026")
    const mdyText = s.match(/^([a-zA-Z]{3,})\s+(\d{1,2}),?\s+(\d{4})$/);
    if (mdyText) {
        const [, mon, d, y] = mdyText;
        const m = MONTHS[mon.slice(0, 3).toLowerCase()];
        if (m) return `${y}-${String(m).padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // Last resort: native Date parse
    const parsed = new Date(s);
    if (!isNaN(parsed.getTime())) return parsed.toISOString().split('T')[0];

    return null;
}

/**
 * Strips currency symbols (₹, Rs., INR, $, €, commas) and returns a clean float.
 */
function sanitizeCurrencyValue(val) {
    if (typeof val === 'number') return val;
    const cleaned = String(val)
        .replace(/Rs\.?/gi, '')
        .replace(/INR/gi, '')
        .replace(/[₹$€£,\s]/g, '')
        .trim();
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
}

/**
 * Validates all required fields on the extracted receipt object.
 * Returns an array of error strings — empty means valid.
 */
function validateReceiptFields(data) {
    const errors = [];
    if (!data.rawMerchant || String(data.rawMerchant).trim() === '') errors.push('missing merchant name');
    if (!data.date) errors.push('missing date');
    if (!data.total || data.total <= 0) errors.push('invalid or missing total amount');
    if (!Array.isArray(data.items)) errors.push('items field is not an array');
    return errors;
}

// Generates a random 12-digit numeric code displayed to the user after claiming a reward
function generateClaimCode() {
    let code = "";
    for (let i = 0; i < 12; i += 1) {
        code += Math.floor(Math.random() * 10);
    }
    return code;
}

initializeFirebaseAdmin();
const db = admin.firestore();
const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, '../frontend/public')));

const JWT_SECRET = process.env.JWT_SECRET || 'super_secret_bits_pilani_123';

// ── AUTH MIDDLEWARE ────────────────────────────────────────────
// Verifies JWT from Authorization: Bearer <token> header on every protected route
function authenticateToken(req, res, next) {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Access denied.' });

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) return res.status(403).json({ error: 'Invalid token. Please log in again.' });
        req.userId = user.userId;
        next();
    });
}

// ── REWARD ENGINE ──────────────────────────────────────────────
// Points formula: ₹100 = 1 base pt → multiplied by category, tier, and streak bonuses
// Grocery +20% | Food & Beverage +50% | Premium tier +50% | Streak +30%
//
// NOTE: `streak` is stored on the user and read here, but nothing in the system
// ever sets it after the document is created — there is no daily-activity
// calculation. Both creation paths seed it false, so the +30% branch is
// currently unreachable in practice. It is left in place because the reward
// formula is documented in the report; awarding it needs a streak calculation
// that does not exist yet.
function calculateRewards(totalAmount, category, isStreak = false, tier = "Standard") {
    let points = 0;
    let logicText = "";

    const basePoints = Math.floor(totalAmount / 100);
    points += basePoints;
    logicText += `Base: ${basePoints} pts (₹100 = 1pt). `;

    let multiplier = 1.0;
    if (category === 'Supermarket / Grocery') multiplier += 0.2;
    else if (category === 'Food & Beverage') multiplier += 0.5;

    if (tier === 'Premium') multiplier += 0.5;
    if (isStreak) {
        multiplier += 0.3;
        logicText += `Streak Bonus! `;
    }

    if (multiplier > 1.0) {
        points = Math.floor(points * multiplier);
        logicText += `Multiplier: ${multiplier.toFixed(1)}x applied. `;
    }

    if (points === 0 && totalAmount > 0) points = 1;
    return { points, logicText };
}

// Creates a user document in Firestore if it doesn't exist, then returns its ref
async function ensureUserExists(userId) {
    if (!userId) throw new Error("userId missing in ensureUserExists");
    const userRef = db.collection('Users').doc(userId);
    const doc = await userRef.get();
    if (!doc.exists) {
        await userRef.set({
            total_points: 0,
            tier: 'Standard',
            // false, matching /api/signup. This path used to seed `true`, so a
            // user document created here rather than at signup earned the +30%
            // streak multiplier on every receipt, permanently — nothing
            // recomputes the flag — while a normally registered user never did.
            // Two users with identical behaviour were paid at different rates
            // depending on which code path happened to create their document.
            streak: false,
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });
    }
    return userRef;
}

// ── API ROUTES ─────────────────────────────────────────────────

// POST /api/signup — creates new user, hashes password with bcrypt, returns 24h JWT
app.post('/api/signup', async (req, res) => {
    try {
        const { email, password, name } = req.body || {};
        const normalizedEmail = normalizeEmail(email);
        if (!normalizedEmail || !password) return res.status(400).json({ error: 'Email and password required' });

        const usersSnapshot = await db.collection('Users').where('email', '==', normalizedEmail).limit(1).get();
        if (!usersSnapshot.empty) return res.status(409).json({ error: 'Email already exists.' });

        const hashedPassword = await bcrypt.hash(password, 10);
        const newUserRef = db.collection('Users').doc();

        await newUserRef.set({
            email: normalizedEmail,
            password: hashedPassword,
            name: name || 'User',
            total_points: 0,
            tier: 'Standard',
            streak: false,
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });

        const token = jwt.sign({ userId: newUserRef.id }, JWT_SECRET, { expiresIn: '24h' });
        res.json({ token, name: name || 'User' });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// POST /api/login — verifies bcrypt password hash, returns JWT + user name
app.post('/api/login', async (req, res) => {
    try {
        const { email, password } = req.body || {};
        const normalizedEmail = normalizeEmail(email);
        if (!normalizedEmail || !password) return res.status(400).json({ error: 'Email and password required.' });

        const usersSnapshot = await db.collection('Users').where('email', '==', normalizedEmail).limit(1).get();

        if (usersSnapshot.empty) return res.status(401).json({ error: 'Invalid email or password.' });

        const userDoc = usersSnapshot.docs[0];
        const userData = userDoc.data();

        const match = await bcrypt.compare(password, userData.password);
        if (!match) return res.status(401).json({ error: 'Invalid email or password.' });

        const token = jwt.sign({ userId: userDoc.id }, JWT_SECRET, { expiresIn: '24h' });
        res.json({ token, name: userData.name });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/user — returns current point balance and display name (auth required)
app.get('/api/user', authenticateToken, async (req, res) => {
    try {
        const userRef = await ensureUserExists(req.userId);
        const doc = await userRef.get();
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
        res.json({ totalPoints: doc.data().total_points || 0, name: doc.data().name || 'User' });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/history — returns all receipts scanned by this user, sorted newest-first
// Sorted client-side to avoid requiring a Firestore composite index
app.get('/api/history', authenticateToken, async (req, res) => {
    try {
        const snapshot = await db.collection('Receipts')
            .where('user_id', '==', req.userId)
            .get();

        const history = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            if (data.created_at && data.created_at.toDate) {
                data.created_at = data.created_at.toDate().toISOString();
            }
            history.push({ id: doc.id, ...data });
        });

        // Sort manually to bypass forced composite index requirement in Firestore
        history.sort((a, b) => {
            const aTs = Date.parse(a.created_at || '') || 0;
            const bTs = Date.parse(b.created_at || '') || 0;
            return bTs - aTs;
        });

        // Cache control
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
        res.json({ history });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/receipt/:id — returns single receipt + its line items; enforces ownership check
app.get('/api/receipt/:id', authenticateToken, async (req, res) => {
    try {
        const receiptId = String(req.params.id || '').trim();
        if (!receiptId) return res.status(400).json({ error: 'Receipt ID is required.' });

        const receiptRef = db.collection('Receipts').doc(receiptId);
        const receiptDoc = await receiptRef.get();
        if (!receiptDoc.exists) {
            return res.status(404).json({ error: 'Receipt not found.' });
        }

        const receiptData = receiptDoc.data();
        if (receiptData.user_id !== req.userId) {
            return res.status(403).json({ error: 'Unauthorized receipt access.' });
        }

        const itemsSnapshot = await db.collection('Receipt_Items')
            .where('receipt_id', '==', receiptId)
            .get();

        const items = [];
        itemsSnapshot.forEach(doc => {
            const item = doc.data();
            items.push({
                id: doc.id,
                name: item.name || 'Item',
                price: Number(item.price || 0)
            });
        });

        if (receiptData.created_at && receiptData.created_at.toDate) {
            receiptData.created_at = receiptData.created_at.toDate().toISOString();
        }

        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
        res.json({
            receipt: { id: receiptId, ...receiptData },
            items
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/analytics — aggregates all receipts into spend summary + category chart + insights
app.get('/api/analytics', authenticateToken, async (req, res) => {
    try {
        const snapshot = await db.collection('Receipts')
            .where('user_id', '==', req.userId)
            .get();

        const receipts = [];
        snapshot.forEach(doc => {
            receipts.push(doc.data());
        });

        if (receipts.length === 0) {
            return res.json({
                success: true,
                hasData: false,
                summary: {
                    totalBills: 0,
                    totalSpend: 0,
                    avgBillValue: 0,
                    totalPointsEarned: 0,
                    topCategory: '-',
                    topMerchant: '-'
                },
                categories: [],
                insights: []
            });
        }

        let totalSpend = 0;
        let totalPoints = 0;
        const categoryMap = {};
        const merchantMap = {};

        receipts.forEach(r => {
            const amount = Number(r.total || 0);
            totalSpend += amount;
            totalPoints += Number(r.points_earned || 0);

            const cat = r.category || 'General';
            categoryMap[cat] = (categoryMap[cat] || 0) + amount;

            const merc = r.merchant || 'Unknown';
            merchantMap[merc] = (merchantMap[merc] || 0) + amount;
        });

        // Find Top Category
        const sortedCats = Object.entries(categoryMap).sort((a, b) => b[1] - a[1]);
        const topCategory = sortedCats[0][0];

        // Find Top Merchant
        const sortedMercs = Object.entries(merchantMap).sort((a, b) => b[1] - a[1]);
        const topMerchant = sortedMercs[0][0];

        // Category distribution for chart
        const totalValue = Object.values(categoryMap).reduce((a, b) => a + b, 0);
        const categories = Object.entries(categoryMap).map(([name, value]) => ({
            name,
            value,
            percentage: Math.round((value / totalValue) * 100)
        })).sort((a, b) => b.value - a.value);

        // Simple Insight Generation
        const insights = [];
        if (topCategory === 'Supermarket / Grocery') {
            insights.push({ title: 'Steady Provider', text: 'You spend significantly on essentials. Consider BigBasket vouchers for maximum savings.' });
        } else if (topCategory === 'Food & Beverage') {
            insights.push({ title: 'Gourmet Interest', text: 'Frequent dining detected. Zomato & Domino\'s vouchers might be your best bet.' });
        }

        if (receipts.length > 5) {
            insights.push({ title: 'Consistent Scanner', text: '5+ bills processed! You are building a great data profile for personalized rewards.' });
        } else {
            insights.push({ title: 'Getting Started', text: 'Keep scanning to unlock more detailed AI-driven shopping insights.' });
        }

        if (totalSpend > 5000) {
            insights.push({ title: 'High Value Shopper', text: 'Your monthly spending is above average. Check out Premium tier benefits.' });
        }

        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
        res.json({
            success: true,
            hasData: true,
            summary: {
                totalBills: receipts.length,
                totalSpend: Math.round(totalSpend),
                avgBillValue: Math.round(totalSpend / receipts.length),
                totalPointsEarned: totalPoints,
                topCategory,
                topMerchant
            },
            categories,
            insights
        });

    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/claimed-rewards — returns all vouchers and scratch cards claimed by this user
app.get('/api/claimed-rewards', authenticateToken, async (req, res) => {
    try {
        const snapshot = await db.collection('Claimed_Rewards')
            .where('user_id', '==', req.userId)
            .get();

        const claims = [];
        snapshot.forEach(doc => {
            const data = doc.data();
            if (data.created_at && data.created_at.toDate) {
                data.created_at = data.created_at.toDate().toISOString();
            }
            claims.push({ id: doc.id, ...data });
        });

        claims.sort((a, b) => {
            const aTs = Date.parse(a.created_at || '') || 0;
            const bTs = Date.parse(b.created_at || '') || 0;
            return bTs - aTs;
        });

        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
        res.json({ claims });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// GET /api/recommendations — reward offers ranked for this user by the ML service.
// Lets the claim modal personalise without waiting for a scan. Returns an empty
// list (not an error) when the ML service is down, so the frontend falls back to
// its own static pool rather than showing nothing.
app.get('/api/recommendations', authenticateToken, async (req, res) => {
    const topN = Math.max(1, Math.min(parseInt(req.query.top_n, 10) || 6, 12));
    try {
        const mlRes = await axios.post(`${ML_SERVICE_URL}/ml/recommend`, {
            user_id: req.userId,
            top_n: topN
        }, { timeout: 3000 });

        res.json({
            recommendations: mlRes.data?.recommendations || [],
            personalised: mlRes.data?.personalised === true,
            model: mlRes.data?.model || 'unavailable'
        });
    } catch (e) {
        console.warn('ML Service (Recommend) unreachable.');
        res.json({ recommendations: [], personalised: false, model: 'unavailable' });
    }
});

// POST /api/claim-reward — atomic Firestore transaction: deducts points + writes claim record
// Throws INSUFFICIENT_POINTS if user balance is too low
app.post('/api/claim-reward', authenticateToken, async (req, res) => {
    try {
        const { type, title, offer, reward, requiredPoints } = req.body || {};
        const claimType = String(type || '').toLowerCase().trim();
        const claimTitle = String(title || '').trim();
        const claimOffer = String(offer || '').trim();
        const claimReward = reward ? String(reward).trim() : null;
        const required = Number.parseInt(requiredPoints, 10);

        if (!['voucher', 'scratch'].includes(claimType)) {
            return res.status(400).json({ error: 'Invalid reward type.' });
        }
        if (!claimTitle) return res.status(400).json({ error: 'Reward title is required.' });
        if (!Number.isInteger(required) || required <= 0) {
            return res.status(400).json({ error: 'Required points must be a positive integer.' });
        }

        const userRef = await ensureUserExists(req.userId);
        const claimCode = generateClaimCode();
        const claimRef = db.collection('Claimed_Rewards').doc();
        const nowIso = new Date().toISOString();

        const result = await db.runTransaction(async tx => {
            const userDoc = await tx.get(userRef);
            const currentPoints = Number.parseInt(userDoc.data()?.total_points || 0, 10);
            if (currentPoints < required) {
                throw new Error('INSUFFICIENT_POINTS');
            }

            tx.update(userRef, {
                total_points: admin.firestore.FieldValue.increment(-required)
            });

            tx.set(claimRef, {
                user_id: req.userId,
                type: claimType,
                title: claimTitle,
                offer: claimOffer,
                reward: claimReward,
                required_points: required,
                claim_code: claimCode,
                status: 'claimed',
                created_at: admin.firestore.FieldValue.serverTimestamp(),
                created_at_iso: nowIso
            });

            return {
                remainingPoints: currentPoints - required
            };
        });

        res.json({
            success: true,
            claim: {
                id: claimRef.id,
                type: claimType,
                title: claimTitle,
                offer: claimOffer,
                reward: claimReward,
                required_points: required,
                claim_code: claimCode,
                created_at: nowIso
            },
            remainingPoints: result.remainingPoints
        });
    } catch (e) {
        if (e.message === 'INSUFFICIENT_POINTS') {
            return res.status(409).json({ error: 'Not enough points to claim this reward.' });
        }
        return res.status(500).json({ error: e.message });
    }
});

/**
 * Generates a deterministic fingerprint for a receipt.
 * Used for cross-user duplicate detection — same physical receipt
 * submitted by different accounts produces the same hash.
 */
function generateReceiptFingerprint(merchant, date, total) {
    const raw = `${String(merchant).trim().toLowerCase()}|${String(date).trim()}|${parseFloat(total).toFixed(2)}`;
    return crypto.createHash('sha256').update(raw).digest('hex');
}

// Turns an OCR rejection into something the user can act on.
//
// All of these used to come back as "Scan Failed: Please ensure the receipt is
// clear." — shown inside a modal already titled "Scan Failed", so the phrase
// appeared twice and told the user nothing either time. The causes are not the
// same and do not have the same remedy: a blurred photo needs a steadier
// retake, whereas an image the model could not parse is usually cropped, in
// shadow, or not a receipt at all. Retaking the same shot fixes the first and
// wastes the user's time on the second.
//
// Returns a code as well, so the client can title the dialog properly instead
// of labelling every failure "Scan Failed".
function describeOcrFailure(payload) {
    const body = payload || {};

    if (body.error === 'multi_bill_detected') {
        return {
            code: 'MULTI_BILL',
            error: 'There is more than one receipt in this photo. Please scan them one at a time.'
        };
    }

    // Set by the blur gate in ocr.py, which rejects before spending an API call.
    if (body.reason === 'image_too_blurry') {
        return {
            code: 'IMAGE_TOO_BLURRY',
            error: 'This photo is too blurry to read. Hold the camera steady, make sure the bill '
                 + 'is well lit and fills most of the frame, then take another picture.'
        };
    }

    // Gemini looked at it and could not find a receipt. Different advice: the
    // usual causes are a cropped bill, glare or shadow, or a photo of something
    // that is not a receipt — none of which a steadier hand fixes.
    return {
        code: 'UNREADABLE',
        error: "We couldn't read the details from this image. Check that the whole bill is in "
             + 'frame, in focus and free of glare or shadow — and that the photo is of a receipt.'
    };
}

// POST /api/upload — the core receipt pipeline:
//  1. Validate base64 image + MIME type
//  2. Forward image to ML service /ml/ocr (ocr.py) → rate-limit gate + Gemini extraction
//  3. Sanitise currency + validate required fields
//  4. Per-user and cross-user duplicate fingerprint check
//  5. Calculate reward points (category × tier × streak multipliers)
//  6. Fraud + anomaly scoring via the ML microservice (defaults if unreachable)
//  7. Write to Firestore: Receipts, Receipt_Items, Merchants, Consent_Logs, Fraud_Scores
//
// 6 runs BEFORE 7 deliberately. Two checks can refuse an upload — the content
// fingerprint at step 4, and the perceptual-hash match inside step 6 — and a
// refusal must leave nothing behind. Fraud scoring used to sit after the writes,
// which was safe only while its verdict was advisory.
//
// Latency note: every Firestore call from outside its region costs ~1s, so this
// endpoint is dominated by round trips rather than by work. The four reads at
// step 4 go out together, the two model calls at step 6 go out together, and
// every write at step 7 lands in a single batch — three waits instead of about
// eleven. Anything added here should join one of those groups, not become a
// fourth. ml-service is fast enough that it is not the thing to optimise.
app.post('/api/upload', authenticateToken, async (req, res) => {
    try {
        if (!req.body || !req.body.receipt) {
            return res.status(400).json({ error: 'No image data provided.' });
        }

        const mimeType = String(req.body.mimeType || 'image/jpeg').toLowerCase().trim();
        if (!SUPPORTED_IMAGE_MIME_TYPES.has(mimeType)) {
            return res.status(415).json({ error: 'Unsupported image format. Use JPG, PNG, WEBP, HEIC, or HEIF.' });
        }

        const receiptPayload = String(req.body.receipt).replace(/\s+/g, '');
        if (!isValidBase64String(receiptPayload)) {
            return res.status(400).json({ error: 'Invalid base64 image data.' });
        }

        const imageBuffer = Buffer.from(receiptPayload, 'base64');
        if (!imageBuffer.length || !looksLikeExpectedImageType(imageBuffer, mimeType)) {
            return res.status(422).json({ error: 'Invalid or unreadable image payload.' });
        }

        // Hand the image to the ML service OCR pipeline (ml-service/ocr.py):
        // blur check → rate-limit gate → Gemini extraction (with model fallback) →
        // multi-bill / handwriting / density-anomaly checks → structured JSON.
        // Gemini is invoked there, not here, so it runs exactly once per upload.
        console.log("Processing image via ML OCR service (Gemini)...");
        let receiptData = null;
        try {
            const ocrRes = await axios.post(`${ML_SERVICE_URL}/ml/ocr`, {
                image: receiptPayload,
                mimeType
            });
            receiptData = ocrRes.data;
        } catch (ocrErr) {
            // ocr.py / app.py map blur + multi-bill rejections to HTTP 422
            const status = ocrErr.response && ocrErr.response.status;
            const body = (ocrErr.response && ocrErr.response.data) || {};
            if (status === 422) {
                if (body.reason === 'image_too_blurry') {
                    console.log(`[INFO] Upload refused pre-OCR: blur score ${body.blur_score}`);
                }
                return res.status(422).json(describeOcrFailure(body));
            }
            // The ML service returns 429 when every API key has hit its
            // per-minute quota. That is a wait-and-retry condition, not a fault
            // in the receipt — collapsing it into the generic 503 below told the
            // user their image could not be processed, which is simply untrue
            // and sends them off to re-photograph a perfectly good bill.
            if (status === 429) {
                return res.status(429).json({
                    error: 'The AI service has hit its rate limit. Wait about a minute and try the same receipt again.'
                });
            }
            console.error('[ERROR] OCR service unreachable:', ocrErr.message);
            return res.status(503).json({ error: 'OCR service is unavailable. Please try again shortly.' });
        }

        if (!receiptData || typeof receiptData !== 'object') {
            return res.status(500).json({ error: 'The OCR service returned an unexpected response.' });
        }

        // Surface OCR-level error payloads (returned with HTTP 200 by the ML service)
        if (receiptData.error) {
            if (receiptData.error === 'unreadable' || receiptData.error === 'multi_bill_detected') {
                return res.status(422).json(describeOcrFailure(receiptData));
            }
            if (receiptData.error === 'GEMINI_API_KEY_MISSING') {
                return res.status(503).json({ error: 'GEMINI_API_KEY is not configured on the ML service.' });
            }
            console.error('[ERROR] OCR extraction failed:', receiptData);
            return res.status(502).json({ error: 'The AI model could not process this receipt. Please try again.' });
        }

        // Sanitize currency symbols from total and every item price
        receiptData.total = sanitizeCurrencyValue(receiptData.total);
        if (Array.isArray(receiptData.items)) {
            receiptData.items = receiptData.items.map(item => ({
                ...item,
                price: sanitizeCurrencyValue(item.price)
            }));
        }

        // Validate all required fields are present and non-empty
        const fieldErrors = validateReceiptFields(receiptData);
        if (fieldErrors.length > 0) {
            console.warn('[WARN] Receipt field validation failed:', fieldErrors);
            return res.status(422).json({ error: `Receipt data incomplete: ${fieldErrors.join(', ')}.` });
        }

        // Normalize date to YYYY-MM-DD regardless of source format
        const normalizedDate = normalizeReceiptDate(receiptData.date);
        if (!normalizedDate) {
            return res.status(422).json({ error: 'Could not parse receipt date. Please try a clearer image.' });
        }
        receiptData.date = normalizedDate;

        const rawMerchant = String(receiptData.rawMerchant || '').trim();
        const normalizedMerchant = normalizeMerchantName(rawMerchant);
        const receiptDate = normalizedDate;
        const total = receiptData.total;
        const receiptFingerprint = generateReceiptFingerprint(rawMerchant, receiptDate, total);

        // Category: prefer the trained ML classifier (Notebook 02), fall back to Gemini's.
        // Non-breaking: if the ML service or model is unavailable, we keep the OCR category.
        // We keep Gemini's original as gemini_category for transparency/comparison.
        const geminiCategory = receiptData.category;
        try {
            const itemsText = Array.isArray(receiptData.items)
                ? receiptData.items.map(it => it.name).filter(Boolean).join(', ')
                : '';
            const classifyRes = await axios.post(`${ML_SERVICE_URL}/ml/classify`, {
                items_text: itemsText,
                merchant: rawMerchant
            });
            const ml = classifyRes.data || {};
            if (ml.model_ready && ml.category && ml.confidence >= CLASSIFIER_MIN_CONFIDENCE) {
                receiptData.category = ml.category;
                receiptData.ml_confidence = ml.confidence;
                console.log(`[INFO] Category from classifier: ${ml.category} (conf ${ml.confidence}); Gemini said ${geminiCategory}`);
            } else {
                console.log(`[INFO] Classifier not confident/ready (${JSON.stringify(ml)}); keeping Gemini category ${geminiCategory}`);
            }
        } catch (clsErr) {
            console.warn('[WARN] /ml/classify unreachable — keeping Gemini category.', clsErr.message);
        }
        receiptData.gemini_category = geminiCategory;

        // Items total cross-check: flag if sum of items deviates >15% from stated total
        let itemsMismatch = false;
        if (Array.isArray(receiptData.items) && receiptData.items.length > 0) {
            const itemsSum = receiptData.items.reduce((sum, item) => sum + (item.price || 0), 0);
            if (itemsSum > 0) {
                const discrepancy = Math.abs(total - itemsSum) / total;
                if (discrepancy > 0.15) {
                    console.warn(`[WARN] Items sum ₹${itemsSum.toFixed(2)} vs stated total ₹${total.toFixed(2)} — ${(discrepancy * 100).toFixed(1)}% discrepancy`);
                    itemsMismatch = true;
                }
            }
        }

        // ── The four reads this upload needs, issued together ──────────────
        //
        // Each Firestore round trip costs roughly a second from here, and these
        // four ran one after another — about 5s of the ~13s an upload took, all
        // of it spent waiting rather than computing. None of them depends on
        // another's result, so they go out together and cost one round trip.
        //
        // The checks below still apply IN THE SAME ORDER, so which error a bad
        // upload gets back is unchanged. The only difference is that all four
        // queries always run, where before a per-user duplicate would have
        // short-circuited the rest — that costs nothing extra, because they
        // are already in flight by the time the first result is examined.
        const [userDuplicateCheck, fuzzyCandidates, crossUserDuplicateCheck, recentHashDocs] =
            await Promise.all([
                db.collection('Receipts')
                    .where('user_id', '==', req.userId)
                    .where('receipt_fingerprint', '==', receiptFingerprint)
                    .limit(1).get(),
                db.collection('Receipts')
                    .where('user_id', '==', req.userId)
                    .where('date', '==', receiptDate)
                    .limit(80).get(),
                db.collection('Receipts')
                    .where('receipt_fingerprint', '==', receiptFingerprint)
                    .limit(1).get(),
                // Perceptual hashes for the near-duplicate check further down.
                // Resolved to null rather than thrown: comparing against nothing
                // is the old behaviour, not a reason to fail the upload — and in
                // a Promise.all one rejection would take the other three with it.
                db.collection('Receipts')
                    .orderBy('created_at', 'desc')
                    .limit(PHASH_LOOKBACK).get()
                    .catch(hashErr => {
                        console.warn("Could not load recent perceptual hashes:", hashErr.message);
                        return null;
                    })
            ]);

        // Per-user exact duplicate check via SHA-256 fingerprint (merchant|date|total)
        if (!userDuplicateCheck.empty) {
            return res.status(409).json({ error: "Duplicate receipt detected. This receipt has already been processed." });
        }

        // Fuzzy duplicate check: catches merchant name typos and ±₹2 total variance on same date
        const fuzzyDuplicate = fuzzyCandidates.docs.find(doc => {
            const data = doc.data() || {};
            if (Math.abs((parseFloat(data.total) || 0) - total) > 2.0) return false;
            return merchantSimilarityScore(data.merchant, rawMerchant) >= 0.84;
        });

        if (fuzzyDuplicate) {
            return res.status(409).json({ error: "Possible duplicate receipt detected (fuzzy match). Please verify merchant/date/total before re-uploading." });
        }

        // Cross-user duplicate check: same physical receipt submitted by a different account
        const crossUserDuplicate = !crossUserDuplicateCheck.empty;

        // One physical receipt earns a reward once. A fingerprint match across
        // accounts is the double-dipping case the cross-user check exists to
        // stop, so it blocks the claim rather than only colouring a badge —
        // previously the second account was flagged High risk and still credited
        // the full points, which made the control advisory.
        //
        // First upload wins. That does penalise a genuine owner who submits
        // after someone else has already claimed their bill, which is why the
        // message points at support instead of accusing the user.
        if (crossUserDuplicate) {
            console.warn(`[FRAUD] Cross-user duplicate blocked for fingerprint ${receiptFingerprint} (user ${req.userId})`);

            // A blocked attempt is the control doing its job, and it leaves no
            // receipt behind — so without this row the only evidence it ever
            // fired is a console line. Logged with `blocked: true` so audit
            // queries can separate prevented claims from scored ones, and with
            // the winning receipt's id so a disputed bill can be traced.
            //
            // score is null on purpose: the block happens before the fraud
            // model runs, and recording a number we never computed would put a
            // fabricated score in the audit trail.
            try {
                const claimedBy = crossUserDuplicateCheck.docs[0];
                await db.collection('Fraud_Scores').doc().set({
                    receipt_id: null,
                    user_id: req.userId,
                    score: null,
                    risk_level: 'Blocked',
                    blocked: true,
                    blocked_reason: 'cross_user_duplicate',
                    receipt_fingerprint: receiptFingerprint,
                    claimed_by_receipt_id: claimedBy ? claimedBy.id : null,
                    claimed_by_user_id: claimedBy ? (claimedBy.data() || {}).user_id || null : null,
                    cross_user_duplicate: true,
                    timestamp: admin.firestore.FieldValue.serverTimestamp()
                });
            } catch (auditErr) {
                // Never fail the block because the audit write failed — the
                // user must still be told, and the console line survives.
                console.error('[FRAUD] Could not log blocked attempt:', auditErr.message);
            }

            return res.status(409).json({
                code: 'ALREADY_CLAIMED',
                error: "This bill has already been claimed on another account. Each receipt can be rewarded only once. If you believe this is a mistake, please contact support."
            });
        }

        // Processing Tier / Multipiler
        const userRef = await ensureUserExists(req.userId);
        const userDoc = await userRef.get();
        const userData = userDoc.data();
        const rewardResult = calculateRewards(total, receiptData.category, userData.streak || false, userData.tier || "Standard");

        // ---- Phase 2 Schema Database Synchronization ----

        // Merchant document id.
        //
        // Stripping everything outside [a-zA-Z0-9] assumes a Latin-script name.
        // A Hindi bill ("श्रीराम वस्त्रालय") sanitises to "_________________",
        // which is non-empty — so the old `if (!merchantId)` guard passed it
        // through — and Firestore reserves every id matching __.*__, so the
        // whole upload died with a 500 at the Merchants write. The same is true
        // of Tamil, Arabic, Chinese, or any shop whose name is punctuation.
        //
        // Fall back to a hash of the normalised name: valid in any script, and
        // stable, so one shop keeps one merchant record across uploads. Latin
        // names keep their existing readable ids, so nothing already stored
        // needs migrating.
        let merchantId = receiptData.rawMerchant.replace(/[^a-zA-Z0-9]/g, '_').slice(0, 100);
        if (!/[a-zA-Z0-9]/.test(merchantId) || /^__.*__$/.test(merchantId)) {
            const basis = normalizedMerchant || rawMerchant || 'unknown';
            merchantId = 'm_' + crypto.createHash('sha256').update(basis).digest('hex').slice(0, 16);
        }

        // ── Fraud + anomaly scoring, BEFORE anything is written ────────────
        //
        // This used to run at step 6, after the receipt, its line items, the
        // points and the consent log had all been committed. That was fine
        // while the score was advisory, but a perceptual-hash match now
        // REJECTS the upload, and rejecting after five writes would mean
        // unpicking them. Nothing here needs the receipt to exist first.
        let fraudScore = 0.05;
        let riskLevel = "Low";
        let fraudSignals = {};
        let tamperProbability = null;
        let imagePhash = null;
        // Perceptual hashes of recent receipts. fraud.py can only compare against
        // hashes it is handed, and nothing here ever stored or sent one — so the
        // duplicate signal was implemented, documented as live, and returned false
        // on every upload since it was written.
        //
        // This is a NEAR-duplicate check, which is why it earns its place next to
        // the SHA-256 fingerprint above: that catches an identical resubmission,
        // but the same bill photographed twice yields different bytes, different
        // OCR text and a different fingerprint, while still hashing close here.
        //
        // Fetched with the duplicate queries above, not here — it is a read like
        // the others and there is no reason to pay a second round trip for it.
        // Hash AND total. The hash alone is not enough to refuse an upload:
        // different receipts collide perceptually (they are all pale paper with
        // a dark text block), and a bare-hash match wrongly blocked a genuine
        // receipt during demo recording. fraud.py requires the totals to agree
        // before it will call it a duplicate.
        const knownHashes = recentHashDocs
            ? recentHashDocs.docs
                .map(doc => {
                    const d = doc.data() || {};
                    return d.image_phash ? { hash: d.image_phash, total: d.total } : null;
                })
                .filter(Boolean)
            : [];

        // Spending anomaly (Isolation Forest) — flags an amount that is unusual
        // for this user and category.
        let anomalyScore = 0.05;
        let anomalyFlag = false;

        // Both models are asked at once. They share no inputs and neither reads
        // the other's answer, so running them back to back only added their
        // latencies together. Each call keeps its own catch, so an unreachable
        // ML service still degrades to the documented defaults rather than
        // failing the upload — and one model being down cannot take the other
        // with it.
        const [fraudRes, anomalyRes] = await Promise.all([
            // The image goes with it. Without it the ML service can only apply
            // the OCR rule signals — the perceptual-hash duplicate check and the
            // 448px tamper CNN both need the pixels, and silently score nothing
            // when they are absent.
            axios.post(`${ML_SERVICE_URL}/ml/fraud-score`, {
                ocr_result: receiptData,
                image: receiptPayload,
                mimeType,
                known_hashes: knownHashes
            }).catch(() => {
                console.warn("ML Service (Fraud) unreachable, using simulation defaults.");
                return null;
            }),
            axios.post(`${ML_SERVICE_URL}/ml/anomaly`, {
                user_id: req.userId,
                amount: total,
                category: receiptData.category,
                date: receiptData.date
            }).catch(() => {
                console.warn("ML Service (Anomaly) unreachable, using simulation defaults.");
                return null;
            })
        ]);

        if (anomalyRes && anomalyRes.data && anomalyRes.data.anomaly_score !== undefined) {
            anomalyScore = anomalyRes.data.anomaly_score;
            anomalyFlag = anomalyRes.data.is_anomaly === true;
        }

        {
            if (fraudRes && fraudRes.data && fraudRes.data.fraud_score !== undefined) {
                fraudScore = fraudRes.data.fraud_score;
                // Which signals actually fired. fraud.py already computes this;
                // without forwarding it the client can only guess why a score is
                // what it is, and guessing produced a misleading explanation.
                fraudSignals = fraudRes.data.signals || {};
                tamperProbability = fraudRes.data.tamper_probability ?? null;
                riskLevel = fraudScore > 0.7 ? "High" : (fraudScore > 0.3 ? "Medium" : "Low");

                // Carried into the receipt's initial write below, so the NEXT
                // upload has something to compare against. This used to be a
                // second update() after the receipt existed; now the receipt is
                // written after scoring, so one write does it.
                imagePhash = fraudRes.data.image_phash || null;
            }
        }

        // No cross-user branch here any more: that case now returns 409
        // ALREADY_CLAIMED before any of this runs, so escalating the score was
        // unreachable code describing a path the request can no longer take.

        // Items/total mismatch → bump to at least Medium
        if (itemsMismatch) {
            fraudScore = Math.max(fraudScore, 0.5);
            if (riskLevel === "Low") riskLevel = "Medium";
        }


        // A near-duplicate image is refused outright.
        //
        // The SHA-256 fingerprint above catches a byte-identical resubmission.
        // This catches the same bill photographed a second time, cropped or
        // re-compressed — different bytes, often different OCR text, but the
        // same picture. One physical receipt earns a reward once.
        //
        // Deliberately NOT applied to the tamper CNN. At AUC 0.805 it is a
        // review signal, not a verdict, and auto-rejecting on it would refuse
        // genuine receipts. The model card says it is not a rejection gate; this
        // keeps that true.
        if (fraudSignals.duplicate) {
            console.warn(`[FRAUD] Near-duplicate image blocked (phash ${imagePhash}) for user ${req.userId}`);
            try {
                await db.collection('Fraud_Scores').doc().set({
                    receipt_id: null,
                    user_id: req.userId,
                    score: fraudScore,
                    risk_level: riskLevel,
                    blocked: true,
                    blocked_reason: 'perceptual_duplicate',
                    image_phash: imagePhash,
                    timestamp: admin.firestore.FieldValue.serverTimestamp()
                });
            } catch (auditErr) {
                console.error('[FRAUD] Could not log blocked near-duplicate:', auditErr.message);
            }
            return res.status(409).json({
                code: 'DUPLICATE_IMAGE',
                error: "This photo matches a receipt already in the system. Each receipt can be rewarded only once — if you believe this is a mistake, please contact support."
            });
        }


        // An anomalous spend is a fraud-adjacent signal → nudge risk to at least Medium.
        if (anomalyFlag && riskLevel === "Low") riskLevel = "Medium";

        // ── Every write this upload makes, committed once ──────────────────
        //
        // These were six separate awaits — merchant, receipt, items, points,
        // consent log, fraud score — and each one paid a full round trip, about
        // 6s of the ~13s an upload took. A Firestore batch of five writes costs
        // roughly what a single write costs, so they now go together.
        //
        // The batch is also atomic, which the sequence was not. That matters
        // here: a failure halfway through used to leave a receipt with no points
        // or points with no fraud record, and this endpoint already refuses
        // uploads part-way (duplicate, near-duplicate) on the promise that a
        // refusal writes nothing.
        const merchantRef = db.collection('Merchants').doc(merchantId);
        const newReceiptRef = db.collection('Receipts').doc();
        const writes = db.batch();

        // Merchants upsert
        writes.set(merchantRef, {
            name: receiptData.rawMerchant,
            normalized_category: receiptData.category,
            last_seen: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });

        // Receipt
        writes.set(newReceiptRef, {
            user_id: req.userId,
            merchant: rawMerchant,
            merchant_normalized: normalizedMerchant,
            merchant_id: merchantRef.id,
            date: receiptDate,
            total: total,
            category: receiptData.category,
            points_earned: rewardResult.points,
            receipt_fingerprint: receiptFingerprint,
            image_phash: imagePhash,
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });

        // Running point total. increment() is atomic server-side, so batching it
        // is as safe as the standalone update it replaces.
        writes.update(userRef, {
            total_points: admin.firestore.FieldValue.increment(rewardResult.points)
        });

        // Consent log (Section 5.4 Privacy Rules)
        writes.set(db.collection('Consent_Logs').doc(), {
            user_id: req.userId,
            action: "receipt_scan",
            status: "granted",
            data_points: ["merchant", "total", "category"],
            timestamp: admin.firestore.FieldValue.serverTimestamp()
        });

        // Fraud + anomaly verdict
        writes.set(db.collection('Fraud_Scores').doc(), {
            receipt_id: newReceiptRef.id,
            user_id: req.userId,
            score: fraudScore,
            risk_level: riskLevel,
            cross_user_duplicate: crossUserDuplicate,
            items_total_mismatch: itemsMismatch,
            anomaly_score: anomalyScore,
            anomaly_flag: anomalyFlag,
            timestamp: admin.firestore.FieldValue.serverTimestamp()
        });

        // Line items. A batch caps at 500 operations and five are already used,
        // so a freak receipt with hundreds of lines spills into follow-up
        // batches rather than throwing.
        const items = Array.isArray(receiptData.items) ? receiptData.items : [];
        const INLINE_ITEM_LIMIT = 450;
        items.slice(0, INLINE_ITEM_LIMIT).forEach(item => {
            writes.set(db.collection('Receipt_Items').doc(), {
                receipt_id: newReceiptRef.id,
                name: item.name,
                price: item.price
            });
        });

        const overflow = [];
        for (let i = INLINE_ITEM_LIMIT; i < items.length; i += INLINE_ITEM_LIMIT) {
            const extra = db.batch();
            items.slice(i, i + INLINE_ITEM_LIMIT).forEach(item => {
                extra.set(db.collection('Receipt_Items').doc(), {
                    receipt_id: newReceiptRef.id,
                    name: item.name,
                    price: item.price
                });
            });
            overflow.push(extra.commit());
        }

        await Promise.all([writes.commit(), ...overflow]);

        // ── Interest vector, then the offers ranked against it ─────────────
        // Update the user's spend-interest vector in the ML service.
        //    Awaited (not fire-and-forget) so the recommendations below reflect the
        //    receipt that was just scanned. It is a local JSON write, so the added
        //    latency is small, and a failure must never fail the upload.
        try {
            await axios.post(`${ML_SERVICE_URL}/ml/update-profile`, {
                user_id: req.userId,
                category: receiptData.category,
                amount: total,
                merchant: receiptData.rawMerchant
            }, { timeout: 3000 });
        } catch (mlError) {
            console.warn("ML Service (Profile) update failed.");
        }

        // Personalised reward offers, ranked against that interest vector.
        let recommendedRewards = [];
        try {
            const recRes = await axios.post(`${ML_SERVICE_URL}/ml/recommend`, {
                user_id: req.userId,
                top_n: 5
            }, { timeout: 3000 });
            if (recRes.data && Array.isArray(recRes.data.recommendations)) {
                recommendedRewards = recRes.data.recommendations;
            }
        } catch (mlError) {
            console.warn("ML Service (Recommend) unreachable, frontend will use its default pool.");
        }

        res.json({
            success: true,
            data: {
                ...receiptData,
                receiptId: newReceiptRef.id,
                rewardPoints: rewardResult.points,
                rewardLogic: rewardResult.logicText,
                fraudScore: fraudScore,
                riskLevel: riskLevel,
                anomalyScore: anomalyScore,
                anomalyFlag: anomalyFlag,
                // Why the risk level is what it is, so the client can explain the
                // verdict instead of showing an unexplained score.
                crossUserDuplicate: crossUserDuplicate,
                itemsTotalMismatch: itemsMismatch,
                fraudSignals: fraudSignals,
                // What the tamper CNN itself returned, separate from the blended
                // score. The client was showing the blended figure labelled as a
                // tamper score, which is not the same number.
                tamperProbability: tamperProbability,
                recommendedRewards: recommendedRewards
            }
        });

    } catch (error) {
        console.error('OCR Error:', error);

        // Handle Google API Rate Limiting Graciously
        if (error.status === 429 || (error.error && error.error.code === 429)) {
            return res.status(429).json({ error: 'AI processing quota has been exceeded. Please wait a moment and try again.' });
        }

        res.status(500).json({ error: 'Internal server error processing the receipt.' });
    }
});

app.listen(port, () => console.log(`🚀 Server running dynamically on http://localhost:${port}`));
