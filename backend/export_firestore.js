/**
 * Export real user receipt history from Firestore → CSV for the ML notebooks.
 * This is the user-interaction data the collaborative filter (Notebook 04) and
 * anomaly scorer need — it does not exist in receipts_master.csv (that's the
 * external CORD/SROIE data, not per-user activity).
 *
 * Writes dataset/processed/firestore_receipts.csv with one row per receipt.
 * Run: node backend/export_firestore.js
 */
const fs = require('fs');
const path = require('path');
const admin = require('firebase-admin');

admin.initializeApp({ credential: admin.credential.cert(require('./serviceAccountKey.json')) });
const db = admin.firestore();

const OUT = path.join(__dirname, '..', 'dataset', 'processed', 'firestore_receipts.csv');
const FIELDS = ['user_id', 'merchant', 'category', 'total', 'points_earned', 'date', 'created_at'];

function csvCell(v) {
  if (v === undefined || v === null) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

(async () => {
  try {
    const snap = await db.collection('Receipts').orderBy('created_at').get();
    const rows = [FIELDS.join(',')];
    const users = new Set();
    const cats = {};
    snap.forEach(doc => {
      const r = doc.data();
      users.add(r.user_id);
      cats[r.category] = (cats[r.category] || 0) + 1;
      const created = r.created_at && r.created_at.toDate ? r.created_at.toDate().toISOString() : '';
      rows.push([r.user_id, r.merchant, r.category, r.total, r.points_earned, r.date, created]
        .map(csvCell).join(','));
    });
    fs.writeFileSync(OUT, rows.join('\n') + '\n');
    console.log(`✅ Exported ${snap.size} receipts → dataset/processed/firestore_receipts.csv`);
    console.log(`   distinct users: ${users.size}`);
    console.log(`   category spread: ${JSON.stringify(cats)}`);
    if (users.size < 10) {
      console.log('   ⚠️  Sparse: too few users for a meaningful collaborative filter yet —');
      console.log('       supplement with synthetic_user_interactions.csv or collect more usage.');
    }
    process.exit(0);
  } catch (e) {
    console.error('❌ Export failed:', e.code || '', e.message);
    process.exit(1);
  }
})();
