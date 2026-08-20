/**
 * Wipes every user-generated document so a demo or test run starts clean.
 *
 * A receipt can only be claimed once, ever — that is the whole point of the
 * fraud controls — so the SECOND take of a recording will be refused with
 * ALREADY_CLAIMED unless the data is cleared between takes. That is correct
 * behaviour, not a fault, and this script is the intended way around it.
 *
 *   node backend/reset_demo_data.js
 *
 * It also clears the ML service's interest-vector cache, which Firestore
 * deletion does not touch and which would otherwise carry personalisation
 * from a previous take into the next one.
 */
const fs = require('fs');
const path = require('path');
const admin = require('firebase-admin');

admin.initializeApp({
    credential: admin.credential.cert(require(path.join(__dirname, 'serviceAccountKey.json')))
});
const db = admin.firestore();

const COLLECTIONS = ['Receipts', 'Receipt_Items', 'Merchants', 'Fraud_Scores',
                     'Consent_Logs', 'Users', 'Claimed_Rewards', 'Anomaly_Scores'];

(async () => {
    for (const name of COLLECTIONS) {
        const snap = await db.collection(name).get();
        if (snap.empty) { console.log(`  ${name.padEnd(16)} already empty`); continue; }
        let batch = db.batch(), n = 0;
        for (const doc of snap.docs) {
            batch.delete(doc.ref);
            if (++n === 400) { await batch.commit(); batch = db.batch(); n = 0; }
        }
        if (n) await batch.commit();
        console.log(`  ${name.padEnd(16)} deleted ${snap.size}`);
    }

    const profiles = path.join(__dirname, '..', 'ml-service', 'models', 'user_profiles.json');
    try { fs.writeFileSync(profiles, '{}\n'); console.log('  user_profiles.json  cleared'); }
    catch (e) { console.warn('  user_profiles.json  not cleared:', e.message); }

    let total = 0;
    for (const name of COLLECTIONS) total += (await db.collection(name).get()).size;
    console.log(`\n  ${total} documents remaining ${total === 0 ? '— clean, ready to record' : '— CHECK'}`);
    process.exit(total === 0 ? 0 : 1);
})();
