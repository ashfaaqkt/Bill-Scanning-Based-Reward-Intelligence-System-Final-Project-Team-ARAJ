require('dotenv').config();
const fs = require('fs');
const path = require('path');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const { GoogleGenAI } = require('@google/genai');
const admin = require('firebase-admin');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5001';
const SERVICE_ACCOUNT_PATH = path.join(__dirname, 'serviceAccountKey.json');
const SUPPORTED_IMAGE_MIME_TYPES = new Set([
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif'
]);

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

function normalizeEmail(email) {
    return String(email || '').trim().toLowerCase();
}

function isValidBase64String(value) {
    return typeof value === 'string'
        && value.length > 0
        && value.length % 4 === 0
        && /^[A-Za-z0-9+/]+={0,2}$/.test(value);
}

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

const ai = process.env.GEMINI_API_KEY ? new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY }) : null;
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const JWT_SECRET = process.env.JWT_SECRET || 'super_secret_bits_pilani_123';

// Auth Middleware
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

// Logic Helper - Validates Reward Engine (FR Requirement)
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

// Ensure user node exists physically in Firestore
async function ensureUserExists(userId) {
    if (!userId) throw new Error("userId missing in ensureUserExists");
    const userRef = db.collection('Users').doc(userId);
    const doc = await userRef.get();
    if (!doc.exists) {
        await userRef.set({
            total_points: 0,
            tier: 'Standard',
            streak: true,
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });
    }
    return userRef;
}

// --- APIs ---

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

let lastGeminiRequestTime = 0;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

app.post('/api/upload', authenticateToken, async (req, res) => {
    try {
        if (!req.body || !req.body.receipt) {
            return res.status(400).json({ error: 'No image data provided.' });
        }

        if (!ai) {
            return res.status(503).json({ error: 'GEMINI_API_KEY is not configured on the server.' });
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

        // Enforce 22s gap between requests (safe margin within 5 RPM free tier limit)
        const RATE_LIMIT_MS = 22000;
        const now = Date.now();
        const elapsed = now - lastGeminiRequestTime;
        if (elapsed < RATE_LIMIT_MS) {
            const waitTime = RATE_LIMIT_MS - elapsed;
            console.log(`[INFO] Rate limiting: Waiting ${(waitTime / 1000).toFixed(1)}s before sending next Gemini request...`);
            await sleep(waitTime);
        }

        console.log("Processing image with Gemini...");
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: [
                {
                    role: 'user',
                    parts: [
                        { text: `Analyze this receipt image and extract the following details into a strict JSON format. If blurry/unreadable return exactly: {"error": "unreadable"}. Otherwise return: {"rawMerchant": "string", "date": "string (YYYY-MM-DD)", "total": number, "category": "string ('Supermarket / Grocery', 'Food & Beverage', or 'General Retail')", "items": [{ "name": "string", "price": number }]}` },
                        { inlineData: { data: receiptPayload, mimeType } }
                    ]
                }
            ],
            config: { responseMimeType: "application/json" }
        });

        // Update last request time AFTER call
        lastGeminiRequestTime = Date.now();

        let textResponse = "";
        if (response && response.text) {
            textResponse = response.text;
        } else if (response && response.candidates && response.candidates[0] && response.candidates[0].content && response.candidates[0].content.parts[0]) {
            textResponse = response.candidates[0].content.parts[0].text;
        }

        let receiptData = null;
        try {
            // Remove markdown code block syntax robustly
            let cleanedText = textResponse.replace(/```json/gi, '').replace(/```/g, '').trim();

            // Try to parse the cleaned text directly first
            try {
                receiptData = JSON.parse(cleanedText);
            } catch (initialParseErr) {
                // Fallback: aggressive extraction for hallucinated text around JSON
                const startIndex = cleanedText.indexOf('{');
                const endIndex = cleanedText.lastIndexOf('}');

                if (startIndex !== -1 && endIndex !== -1 && endIndex > startIndex) {
                    const jsonString = cleanedText.substring(startIndex, endIndex + 1);
                    receiptData = JSON.parse(jsonString);
                } else {
                    throw initialParseErr; // Throw if no brackets found
                }
            }
        } catch (e) {
            console.error("Gemini Parse Failure. Raw Output was:", textResponse);
            return res.status(500).json({ error: "The AI model returned an unreadable format. Please try again." });
        }

        // FR Compliance: 422 Unprocessable Entity
        if (receiptData.error === "unreadable") {
            return res.status(422).json({ error: "Scan Failed: Please ensure the receipt is clear." });
        }

        const total = parseFloat(receiptData.total) || 0;

        // FR Compliance: 409 Conflict checks against real Firestore Database
        const duplicateCheck = await db.collection('Receipts')
            .where('user_id', '==', req.userId)
            .where('merchant', '==', receiptData.rawMerchant)
            .where('date', '==', receiptData.date)
            .where('total', '==', total)
            .get();

        if (!duplicateCheck.empty) {
            return res.status(409).json({ error: "Duplicate receipt detected. This receipt has already been processed." });
        }

        // Processing Tier / Multipiler
        const userRef = await ensureUserExists(req.userId);
        const userDoc = await userRef.get();
        const userData = userDoc.data();
        const rewardResult = calculateRewards(total, receiptData.category, userData.streak || false, userData.tier || "Standard");

        // ---- Phase 2 Schema Database Synchronization ----

        let merchantId = receiptData.rawMerchant.replace(/[^a-zA-Z0-9]/g, '_');
        if (!merchantId) merchantId = "Unknown";

        // 1. Merchants Upsert
        const merchantRef = db.collection('Merchants').doc(merchantId);
        await merchantRef.set({
            name: receiptData.rawMerchant,
            normalized_category: receiptData.category,
            last_seen: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });

        // 2. Receipts
        const newReceiptRef = db.collection('Receipts').doc();
        await newReceiptRef.set({
            user_id: req.userId,
            merchant: receiptData.rawMerchant,
            merchant_id: merchantRef.id,
            date: receiptData.date,
            total: total,
            category: receiptData.category,
            points_earned: rewardResult.points,
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });

        // 3. Receipt Items Batching
        if (receiptData.items && Array.isArray(receiptData.items)) {
            const batch = db.batch();
            receiptData.items.forEach(item => {
                const itemRef = db.collection('Receipt_Items').doc();
                batch.set(itemRef, {
                    receipt_id: newReceiptRef.id,
                    name: item.name,
                    price: item.price
                });
            });
            await batch.commit();
        }

        // 4. Update overall point sum safely
        await userRef.update({
            total_points: admin.firestore.FieldValue.increment(rewardResult.points)
        });

        // 5. Consent Logs (Section 5.4 Privacy Rules)
        const consentRef = db.collection('Consent_Logs').doc();
        await consentRef.set({
            user_id: req.userId,
            action: "receipt_scan",
            status: "granted",
            data_points: ["merchant", "total", "category"],
            timestamp: admin.firestore.FieldValue.serverTimestamp()
        });

        // 6. Fraud System - Call ML Microservice
        let fraudScore = 0.05;
        let riskLevel = "Low";
        try {
            const fraudRes = await axios.post(`${ML_SERVICE_URL}/ml/fraud-score`, {
                receipt_id: newReceiptRef.id,
                metadata: {
                    total: total,
                    merchant: receiptData.rawMerchant,
                    date: receiptData.date
                }
            });
            if (fraudRes.data && fraudRes.data.fraud_score !== undefined) {
                fraudScore = fraudRes.data.fraud_score;
                riskLevel = fraudScore > 0.7 ? "High" : (fraudScore > 0.3 ? "Medium" : "Low");
            }
        } catch (mlError) {
            console.warn("ML Service (Fraud) unreachable, using simulation defaults.");
        }

        const fraudRef = db.collection('Fraud_Scores').doc();
        await fraudRef.set({
            receipt_id: newReceiptRef.id,
            user_id: req.userId,
            score: fraudScore,
            risk_level: riskLevel,
            timestamp: admin.firestore.FieldValue.serverTimestamp()
        });

        // 7. Update User Profile in ML Service (Async)
        axios.post(`${ML_SERVICE_URL}/ml/update-profile`, {
            user_id: req.userId,
            category: receiptData.category,
            amount: total,
            merchant: receiptData.rawMerchant
        }).catch(err => console.warn("ML Service (Profile) update failed."));

        res.json({
            success: true,
            data: {
                ...receiptData,
                receiptId: newReceiptRef.id,
                rewardPoints: rewardResult.points,
                rewardLogic: rewardResult.logicText,
                fraudScore: fraudScore,
                riskLevel: riskLevel
            }
        });

    } catch (error) {
        console.error('OCR Error:', error);

        // Handle Google API Rate Limiting Graciously
        if (error.status === 429 || (error.error && error.error.code === 429)) {
            return res.status(429).json({ error: 'AI processing quota has been exceeded for the free tier. Please wait and try again later.' });
        }

        res.status(500).json({ error: 'Internal server error processing the receipt.' });
    }
});

app.listen(port, () => console.log(`🚀 Server running dynamically on http://localhost:${port}`));
