/**
 * Frontend Logic — Team ARAJ (Ashfaaq Feroz)
 * Handles auth, receipt upload, reward claiming, history, and analytics.
 * Vanilla JS — no framework. Communicates with backend via fetch().
 */

// ── APP STATE ──────────────────────────────────────────────────
let totalPoints = 0;  // In-memory points balance, synced from /api/user

// ── DOM ELEMENT REFERENCES ─────────────────────────────────────
// Stepper progress indicators (Upload → Extract → Process → Reward)
const stepUpload = document.getElementById('step-upload');
const stepExtract = document.getElementById('step-extract');
const stepProcess = document.getElementById('step-process');
const stepReward = document.getElementById('step-reward');

const stageUpload = document.getElementById('stage-upload');
const stageExtracting = document.getElementById('stage-extracting');
const stageResults = document.getElementById('stage-results');

const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const ocrProgress = document.getElementById('ocr-progress');
const ocrProgressPct = document.getElementById('ocr-progress-pct');
const ocrProgressNote = document.getElementById('ocr-progress-note');
const ocrProgressElapsed = document.getElementById('ocr-progress-elapsed');
const ocrProgressMeta = ocrProgressPct ? ocrProgressPct.parentElement : null;

// Result Elements
const valRawMerchant = document.getElementById('val-raw-merchant');
const valDate = document.getElementById('val-date');
const valTotal = document.getElementById('val-total');
const valItems = document.getElementById('val-items');
const valCategory = document.getElementById('val-category');
const valRisk = document.getElementById('val-risk');
const verificationDetail = document.getElementById('verification-detail');
const valFraudScore = document.getElementById('val-fraud-score');
const valAnomaly = document.getElementById('val-anomaly');
const verifyNote = document.getElementById('verify-note');
const valEarnedPoints = document.getElementById('val-earned-points');
const valRewardLogic = document.getElementById('val-reward-logic');
const totalPointsDisplay = document.getElementById('total-points');

// Action Buttons
const btnReset = document.getElementById('btn-reset');
const btnAddBalance = document.getElementById('btn-add-balance');
const btnViewDigitalBill = document.getElementById('btn-view-digital-bill');
const btnViewHistory = document.getElementById('btn-view-history');
const btnCloseHistory = document.getElementById('btn-close-history');
const btnViewAnalytics = document.getElementById('btn-view-analytics');
const btnViewClaimed = document.getElementById('btn-view-claimed');
const btnOpenClaimedFromClaim = document.getElementById('btn-open-claimed-from-claim');
const btnOpenClaimFromClaimed = document.getElementById('btn-open-claim-from-claimed');

// History Section Elements
const sectionHistory = document.getElementById('section-history');
const historyTableBody = document.getElementById('history-table-body');
const historyLoading = document.getElementById('history-loading');
const historyEmpty = document.getElementById('history-empty');
const historyTable = document.querySelector('.history-table');
const claimedModal = document.getElementById('claimed-modal');
const claimedModalBackdrop = document.getElementById('claimed-modal-backdrop');
const claimedModalClose = document.getElementById('claimed-modal-close');
const claimedTableBody = document.getElementById('claimed-table-body');
const claimedLoading = document.getElementById('claimed-loading');
const claimedEmpty = document.getElementById('claimed-empty');

// Auth Elements
const sectionAuth = document.getElementById('section-auth');
const appContent = document.getElementById('app-content');
const authForm = document.getElementById('auth-form');
const authTitle = document.getElementById('auth-title');
const authSubtitle = document.getElementById('auth-subtitle');
const authNameGroup = document.getElementById('auth-name-group');
const authName = document.getElementById('auth-name');
const authEmail = document.getElementById('auth-email');
const authPassword = document.getElementById('auth-password');
const authSubmitBtn = document.getElementById('auth-submit');
const authSwitchText = document.getElementById('auth-switch-text');
const authSwitchLink = document.getElementById('auth-switch-link');
const authError = document.getElementById('auth-error');
const btnLogout = document.getElementById('btn-logout');
const btnTry = document.getElementById('btn-try');
const btnGuest = document.getElementById('btn-guest');
const authModal = document.getElementById('auth-modal');
const authModalClose = document.getElementById('auth-modal-close');
const authModalBackdrop = document.getElementById('auth-modal-backdrop');
const welcomeIntro = document.getElementById('welcome-intro');
const welcomeIntroKicker = document.getElementById('welcome-intro-kicker');
const welcomeIntroText = document.getElementById('welcome-intro-text');
const heroTypingTitle = document.getElementById('hero-typing-title');
const btnClaimPoints = document.getElementById('btn-claim-points');
const claimModal = document.getElementById('claim-modal');
const claimModalClose = document.getElementById('claim-modal-close');
const claimModalBackdrop = document.getElementById('claim-modal-backdrop');
const claimCardsGrid = document.getElementById('claim-cards-grid');
const claimAvailablePoints = document.getElementById('claim-available-points');
const claimSuccessModal = document.getElementById('claim-success-modal');
const claimSuccessBackdrop = document.getElementById('claim-success-backdrop');
const claimSuccessClose = document.getElementById('claim-success-close');
const partyStage = document.getElementById('party-stage');
const claimCodeValue = document.getElementById('claim-code-value');
const btnCopyClaimCode = document.getElementById('btn-copy-claim-code');
const claimSuccessPoints = document.getElementById('claim-success-points');
const digitalBillModal = document.getElementById('digital-bill-modal');
const digitalBillBackdrop = document.getElementById('digital-bill-backdrop');
const digitalBillClose = document.getElementById('digital-bill-close');
const billMerchant = document.getElementById('bill-merchant');
const billDate = document.getElementById('bill-date');
const billCategory = document.getElementById('bill-category');
const billTotal = document.getElementById('bill-total');
const billItemsBody = document.getElementById('bill-items-body');
const billRefCode = document.getElementById('bill-ref-code');

// Analytics DOM Elements
const analyticsModal = document.getElementById('analytics-modal');
const analyticsModalClose = document.getElementById('analytics-modal-close');
const analyticsModalBackdrop = document.getElementById('analytics-modal-backdrop');
const analyticsLoading = document.getElementById('analytics-loading');
const analyticsEmpty = document.getElementById('analytics-empty');
const analyticsContent = document.getElementById('analytics-content');
const analyticsTotalBills = document.getElementById('analytics-total-bills');
const analyticsTotalSpend = document.getElementById('analytics-total-spend');
const analyticsAvgBillValue = document.getElementById('analytics-avg-bill');
const analyticsTotalPoints = document.getElementById('analytics-total-points-earned');
const analyticsTopCategoryLabel = document.getElementById('analytics-top-category-label');
const analyticsTopMerchantLabel = document.getElementById('analytics-top-merchant-label');
const analyticsCategoryChart = document.getElementById('analytics-category-chart');
const analyticsMainInterest = document.getElementById('analytics-main-interest');
const analyticsLegend = document.getElementById('analytics-legend');
const analyticsInsightsList = document.getElementById('analytics-insights-list');
const analyticsFootnote = document.getElementById('analytics-footnote');

// Error Modal DOM Elements
const errorModal = document.getElementById('error-modal');
const errorModalBackdrop = document.getElementById('error-modal-backdrop');
const errorModalClose = document.getElementById('error-modal-close');
const btnErrorOk = document.getElementById('btn-error-ok');
const errorModalIcon = document.getElementById('error-modal-icon');
const errorModalTitle = document.getElementById('error-modal-title');
const errorModalMessage = document.getElementById('error-modal-message');

let claimCodeCopyTimer = null;
let latestProcessedBillData = null;
let currentUserName = 'User';

let isLoginMode = false;
let currentStepIndex = 0;

const STEP_SEQUENCE = [stepUpload, stepExtract, stepProcess, stepReward];

// ── REWARD CATALOG DATA ────────────────────────────────────────
// Static pool of vouchers and scratch cards shown in the claim modal
const VOUCHER_POOL = [
    { icon: '🛒', title: 'BigBasket Voucher', offer: 'Flat ₹150 OFF on groceries' },
    { icon: '🍕', title: 'Domino\'s Voucher', offer: 'Get ₹200 OFF on orders above ₹499' },
    { icon: '🎬', title: 'BookMyShow Pass', offer: 'Buy 1 Get 1 movie ticket' },
    { icon: '☕', title: 'Starbucks Coupon', offer: 'Free Tall Beverage' },
    { icon: '🛍️', title: 'Myntra Voucher', offer: 'Flat ₹300 OFF on fashion' },
    { icon: '🚕', title: 'Uber Credits', offer: '₹250 ride credits' },
    { icon: '📚', title: 'Amazon Books', offer: '₹180 OFF on books' },
    { icon: '🍔', title: 'Zomato Gold', offer: '₹220 OFF food order' },
    { icon: '🎧', title: 'Spotify Premium', offer: '2 months premium access' },
    { icon: '🧾', title: 'Paytm Cashback', offer: '₹100 instant cashback' },
    { icon: '🏨', title: 'OYO Voucher', offer: '₹400 OFF hotel booking' },
    { icon: '💻', title: 'Croma Gift Card', offer: '₹350 OFF electronics' }
];

const SCRATCH_REWARD_POOL = [
    'Win ₹500 Cashback',
    'Win 2X Reward Multiplier',
    'Win Free Coffee Combo',
    'Win ₹300 Gift Voucher',
    'Win ₹250 Grocery Pass',
    'Win Surprise Meal Coupon'
];

// ── SHARED HELPERS ─────────────────────────────────────────────

// Builds Authorization header from JWT stored in localStorage
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

function syncBodyScrollLock() {
    const hasAuthModal = authModal && !authModal.classList.contains('hidden');
    const hasWelcomeIntro = welcomeIntro && !welcomeIntro.classList.contains('hidden');
    const hasClaimModal = claimModal && !claimModal.classList.contains('hidden');
    const hasClaimedModal = claimedModal && !claimedModal.classList.contains('hidden');
    const hasClaimSuccessModal = claimSuccessModal && !claimSuccessModal.classList.contains('hidden');
    const hasDigitalBillModal = digitalBillModal && !digitalBillModal.classList.contains('hidden');
    const hasAnalyticsModal = analyticsModal && !analyticsModal.classList.contains('hidden');
    const hasErrorModal = errorModal && !errorModal.classList.contains('hidden');
    document.body.classList.toggle('modal-open', hasAuthModal || hasWelcomeIntro || hasClaimModal || hasClaimedModal || hasClaimSuccessModal || hasDigitalBillModal || hasAnalyticsModal || hasErrorModal);
}

function randomPick(list) {
    return list[Math.floor(Math.random() * list.length)];
}

function shuffleArray(list) {
    const arr = [...list];
    for (let i = arr.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

function randomIntBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ── CLAIM MODAL — CATALOG & RENDERING ─────────────────────────

// Below this many receipts the interest vector is too thin to shape a reward,
// so scratch cards stay generic rather than pretending to personalise.
const MIN_RECEIPTS_FOR_SCRATCH = 2;
let USER_INTEREST = {};
let USER_RECEIPTS_SEEN = 0;

// Offers ranked for this user by /ml/recommend, refreshed by loadRecommendations().
// Empty until that returns, and left empty if the ML service is unreachable — in
// which case the catalog falls back to the shuffled static pool below.
let RECOMMENDED_OFFERS = [];

// Asks the backend for personalised offers. Never throws: a failure just leaves
// the static pool in place, so the claim modal always has something to show.
async function loadRecommendations() {
    if (!localStorage.getItem('token')) {
        RECOMMENDED_OFFERS = [];   // guest session — nothing to personalise against
        return;
    }
    try {
        const res = await fetch('/api/recommendations?top_n=9', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        RECOMMENDED_OFFERS = Array.isArray(data.recommendations) ? data.recommendations : [];
        // The same response carries the user's category interest vector and how
        // many receipts it was built from. The scratch cards use both.
        USER_INTEREST = data.interest || {};
        USER_RECEIPTS_SEEN = Number(data.receipts_seen) || 0;
    } catch (err) {
        RECOMMENDED_OFFERS = [];
        USER_INTEREST = {};
        USER_RECEIPTS_SEEN = 0;
    }
}

// Scratch rewards drawn from the category the user actually spends in, rather
// than at random. The category is sampled from the interest vector — a user who
// is 70% grocery gets grocery rewards about 70% of the time, so the vault still
// varies without ever offering something unrelated to their spending.
const SCRATCH_BY_CATEGORY = {
    grocery: ['Win a ₹250 Grocery Pass', 'Win 2X points on your next grocery run',
              'Win a Free Delivery Voucher'],
    food:    ['Win a Free Coffee Combo', 'Win a Surprise Meal Coupon',
              'Win 2X points on your next dining bill'],
    retail:  ['Win a ₹300 Fashion Voucher', 'Win a ₹500 Shopping Cashback',
              'Win 2X points on your next retail buy'],
    general: ['Win ₹500 Cashback', 'Win a 2X Reward Multiplier',
              'Win a ₹300 Gift Voucher']
};

function pickInterestCategory() {
    const entries = Object.entries(USER_INTEREST)
        .filter(([, w]) => Number(w) > 0);
    if (!entries.length) return null;

    const total = entries.reduce((sum, [, w]) => sum + Number(w), 0);
    let roll = Math.random() * total;
    for (const [cat, w] of entries) {
        roll -= Number(w);
        if (roll <= 0) return cat;
    }
    return entries[0][0];
}

// Reward value should track how much the user actually spends. Someone with a
// handful of receipts and someone with fifty should not see the same headline.
function scratchTierFor(points) {
    if (points >= 500) return { label: 'Gold', boost: 2.0 };
    if (points >= 200) return { label: 'Silver', boost: 1.5 };
    return { label: 'Bronze', boost: 1.0 };
}

function buildScratchReward(index) {
    const personalised = USER_RECEIPTS_SEEN >= MIN_RECEIPTS_FOR_SCRATCH
        && Object.keys(USER_INTEREST).length > 0;

    if (!personalised) {
        // Guest, or too little history to infer anything — the generic pool,
        // presented as generic.
        return {
            reward: randomPick(SCRATCH_REWARD_POOL),
            category: null,
            tier: null
        };
    }

    const category = pickInterestCategory() || 'general';
    const pool = SCRATCH_BY_CATEGORY[category] || SCRATCH_BY_CATEGORY.general;
    const tier = scratchTierFor(Number(totalPoints) || 0);
    return {
        reward: pool[index % pool.length],
        category: category,
        tier: tier.label
    };
}

// Combines 9 vouchers + 3 scratch cards into the claim catalog. Vouchers come
// from the ML ranking when available — in rank order, best match first — and from
// the shuffled static pool otherwise.
function generateClaimCatalog() {
    const isGuest = currentUserName === 'Guest Explorer';
    const usingRanked = RECOMMENDED_OFFERS.length > 0;

    // A signed-in user sees ONLY what the recommender ranked for them. The
    // static pool is the guest catalogue: falling back to it here would dress
    // a generic list up as personalised, which is exactly the claim the vault
    // is making. No ranking yet means show nothing and keep the skeletons.
    if (!isGuest && !usingRanked) return [];

    const source = usingRanked ? RECOMMENDED_OFFERS : shuffleArray(VOUCHER_POOL);

    const vouchers = [];
    const count = Math.min(9, source.length);
    for (let i = 0; i < count; i += 1) {
        const voucher = source[i];
        vouchers.push({
            type: 'voucher',
            icon: voucher.icon,
            title: voucher.title,
            offer: voucher.offer,
            // The recommender's own explanation — "matches 56% of your recent
            // spend". It was being captured and then never displayed.
            reason: usingRanked ? (voucher.reason || null) : null,
            rank: usingRanked ? i + 1 : null,
            // Cost follows rank rather than a fresh random number each render.
            // randomIntBetween() meant the same voucher cost a different amount
            // every time the modal opened, and made the ordering look arbitrary
            // even when the ranking underneath was not.
            requiredPoints: usingRanked
                ? 30 + i * 5
                : randomIntBetween(20, 90)
        });
    }

    const scratches = [];
    for (let i = 0; i < 3; i += 1) {
        const s = buildScratchReward(i);
        scratches.push({
            type: 'scratch',
            icon: '🃏',
            title: s.tier ? `${s.tier} Scratch Card` : `Scratch & Win Card ${i + 1}`,
            offer: 'Scratch the card to reveal your reward',
            reward: s.reward,
            reason: s.category
                ? `drawn from your ${s.category} spending`
                : null,
            requiredPoints: usingRanked ? 25 + i * 10 : randomIntBetween(20, 90)
        });
    }

    // Signed in: keep the ranking intact. The previous version shuffled the
    // combined list, which threw away the ordering the recommender had just
    // computed — the vault looked random however good the model was. Scratch
    // cards go after the ranked vouchers instead of being dealt through them.
    if (usingRanked) {
        return [...vouchers, ...scratches];
    }

    // Guest: nothing to personalise against, so the static pool is shuffled and
    // presented as the generic catalogue it is.
    return shuffleArray([...vouchers, ...scratches]);
}

function renderClaimCards() {
    if (!claimCardsGrid) return;

    const rewards = generateClaimCatalog();
    const availablePoints = Number(totalPoints) || 0;
    claimCardsGrid.innerHTML = rewards.map((reward) => {
        const canClaim = availablePoints >= Number(reward.requiredPoints);
        if (reward.type === 'scratch') {
            return `
                <article class="claim-card claim-card--scratch ${canClaim ? '' : 'claim-card--locked'}"
                    data-type="scratch"
                    data-title="${reward.title}"
                    data-offer="${reward.offer}"
                    data-reward="${reward.reward}"
                    data-scratched="false"
                    data-required-points="${reward.requiredPoints}">
                    <div class="claim-card-head">
                        <span class="claim-icon">${reward.icon}</span>
                        <span class="claim-type-pill">Scratch</span>
                    </div>
                    <h3>${reward.title}</h3>
                    <p class="claim-offer">${reward.offer}</p>
                    <div class="scratch-shell" data-scratch-shell>
                        <span class="scratch-result">${reward.reward}</span>
                        <canvas class="scratch-canvas" data-scratch-canvas aria-label="Scratch card area"></canvas>
                    </div>
                    <p class="scratch-hint">Scratch card to unlock claim</p>
                    ${reward.reason ? `<p class="claim-reason">🎯 ${reward.reason}</p>` : ''}
                    <p class="claim-required">Required: <strong>${reward.requiredPoints} points</strong></p>
                    <button class="btn btn-secondary" data-scratch-btn disabled>
                        ${canClaim ? 'Scratch to Unlock' : `Need ${reward.requiredPoints} pts`}
                    </button>
                </article>
            `;
        }

        return `
            <article class="claim-card claim-card--voucher ${canClaim ? '' : 'claim-card--locked'}"
                data-type="voucher"
                data-title="${reward.title}"
                data-offer="${reward.offer}"
                data-required-points="${reward.requiredPoints}">
                <div class="claim-card-head">
                    <span class="claim-icon">${reward.icon}</span>
                    <span class="claim-type-pill">Voucher</span>
                </div>
                <h3>${reward.title}</h3>
                <p class="claim-offer">${reward.offer}</p>
                ${reward.reason ? `<p class="claim-reason">🎯 ${reward.reason}</p>` : ''}
                <p class="claim-required">Required: <strong>${reward.requiredPoints} points</strong></p>
                <button class="btn btn-primary" data-voucher-btn ${canClaim ? '' : 'disabled'}>
                    ${canClaim ? 'Claim Voucher' : `Need ${reward.requiredPoints} pts`}
                </button>
            </article>
        `;
    }).join('');
}

function drawScratchOverlay(ctx, width, height) {
    ctx.clearRect(0, 0, width, height);
    const overlay = ctx.createLinearGradient(0, 0, width, height);
    overlay.addColorStop(0, '#cfd6de');
    overlay.addColorStop(0.5, '#eef2f7');
    overlay.addColorStop(1, '#c4ccd6');
    ctx.fillStyle = overlay;
    ctx.fillRect(0, 0, width, height);

    ctx.globalAlpha = 0.2;
    ctx.fillStyle = '#8391a6';
    for (let x = -height; x < width + height; x += 12) {
        ctx.fillRect(x, 0, 4, height);
    }
    ctx.globalAlpha = 1;

    ctx.fillStyle = 'rgba(31, 41, 55, 0.78)';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '600 12px "DM Sans", sans-serif';
    ctx.fillText('Scratch Here', width / 2, height / 2);
}

function getScratchRevealRatio(ctx, width, height) {
    const sample = ctx.getImageData(0, 0, width, height).data;
    let transparentPixels = 0;
    let sampledPixels = 0;
    for (let i = 3; i < sample.length; i += 24) {
        sampledPixels += 1;
        if (sample[i] < 32) transparentPixels += 1;
    }
    return sampledPixels ? transparentPixels / sampledPixels : 0;
}

// ── SCRATCH CARD CANVAS ────────────────────────────────────────
// Draws a grey overlay on a <canvas>; pointer events erase it to reveal the reward
// Tracks reveal ratio — card is "scratched" once 42% of pixels are cleared
function setupScratchCard(card, retries = 0) {
    if (!card) return;
    const shell = card.querySelector('[data-scratch-shell]');
    const canvas = card.querySelector('[data-scratch-canvas]');
    if (!shell || !canvas) return;

    card.dataset.scratched = 'false';
    card.classList.remove('is-scratched');
    canvas.classList.remove('is-cleared');

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return;

    const width = Math.floor(shell.clientWidth);
    const height = Math.floor(shell.clientHeight);
    if ((width < 60 || height < 40) && retries < 6) {
        window.requestAnimationFrame(() => setupScratchCard(card, retries + 1));
        return;
    }
    if (width < 20 || height < 20) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    drawScratchOverlay(ctx, width, height);

    const brush = Math.max(14, Math.floor(width * 0.065));
    let isDrawing = false;
    let lastPoint = null;

    function eraseAt(event) {
        const cRect = canvas.getBoundingClientRect();
        const x = event.clientX - cRect.left;
        const y = event.clientY - cRect.top;
        if (x < 0 || y < 0 || x > cRect.width || y > cRect.height) return;

        ctx.globalCompositeOperation = 'destination-out';
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.lineWidth = brush * 2;

        if (lastPoint) {
            ctx.beginPath();
            ctx.moveTo(lastPoint.x, lastPoint.y);
            ctx.lineTo(x, y);
            ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(x, y, brush, 0, Math.PI * 2);
        ctx.fill();
        lastPoint = { x, y };
    }

    function stopScratch() {
        if (!isDrawing) return;
        isDrawing = false;
        lastPoint = null;

        const revealed = getScratchRevealRatio(ctx, width, height);
        if (revealed >= 0.42) {
            card.dataset.scratched = 'true';
            card.classList.add('is-scratched');
            canvas.classList.add('is-cleared');
            refreshClaimButtonStates();
        }
    }

    canvas.addEventListener('pointerdown', (event) => {
        if (card.dataset.claimed === 'true' || card.dataset.scratched === 'true') return;
        isDrawing = true;
        lastPoint = null;
        canvas.setPointerCapture(event.pointerId);
        eraseAt(event);
    });

    canvas.addEventListener('pointermove', (event) => {
        if (!isDrawing) return;
        eraseAt(event);
    });

    canvas.addEventListener('pointerup', stopScratch);
    canvas.addEventListener('pointercancel', stopScratch);
    canvas.addEventListener('pointerleave', stopScratch);
}

function initScratchCards() {
    claimCardsGrid.querySelectorAll('.claim-card--scratch').forEach((card) => {
        setupScratchCard(card);
    });
}

// How long the vault waits for its background refresh before falling back to
// what is already rendered.
const VAULT_REFRESH_TIMEOUT = 8000;

/** Rejects if `promise` has not settled within `ms`. The underlying request is
    not cancelled — it simply stops being waited on. */
function withTimeout(promise, ms) {
    let timer;
    return Promise.race([
        promise.finally(() => clearTimeout(timer)),
        new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error(`timed out after ${ms}ms`)), ms);
        })
    ]);
}

/** Small "working" pill shown while the vault refreshes in the background.
    The cards are already on screen and usable — this only signals that the
    personalised ranking is still being fetched, so it informs without blocking. */
function setVaultRefreshing(on) {
    if (!claimCardsGrid) return;
    let pill = document.getElementById('vault-refreshing');
    if (on) {
        if (!pill) {
            pill = document.createElement('p');
            pill.id = 'vault-refreshing';
            pill.className = 'vault-refreshing';
            pill.setAttribute('role', 'status');       // announced, not intrusive
            pill.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>'
                           + 'Personalising your offers…';
            claimCardsGrid.parentNode.insertBefore(pill, claimCardsGrid);
        }
        pill.hidden = false;
    } else if (pill) {
        pill.hidden = true;
    }
}

/** Placeholder cards shown while the vault's two network calls are in flight. */
function showClaimSkeletons(count = 4) {
    if (!claimCardsGrid) return;
    claimCardsGrid.innerHTML = Array.from({ length: count }, () => `
        <div class="claim-skeleton" aria-hidden="true">
            <div class="claim-skeleton__line claim-skeleton__line--title"></div>
            <div class="claim-skeleton__line claim-skeleton__line--body"></div>
            <div class="claim-skeleton__line claim-skeleton__line--short"></div>
            <div class="claim-skeleton__line claim-skeleton__line--button"></div>
        </div>`).join('');
}

async function openClaimModal() {
    if (!localStorage.getItem('token') && currentUserName !== 'Guest Explorer') {
        openAuthModal(true);
        return;
    }

    // Paint FIRST, refresh after.
    //
    // This used to await points and the ranked offers before opening, so the
    // click landed on a frozen page for as long as the slower call took. Worse,
    // clicking while the page's own start-up /api/user was still in flight left
    // the second request unresolved in the browser and the vault never opened
    // at all — the server answers both in under a second, so the stall is on the
    // client side of that race.
    //
    // Nothing here needs the network to be useful: the catalogue and the point
    // balance are already in memory. Render them now, then refresh quietly and
    // re-render only if the data actually changed.
    // Signed in, the vault has nothing to show until the ranking arrives, so
    // it opens on skeletons. A guest's catalogue is local, so it paints at once.
    if (localStorage.getItem('token') && !RECOMMENDED_OFFERS.length) {
        showClaimSkeletons();
    } else {
        showClaimCards();
    }
    claimModal.classList.remove('hidden');
    syncBodyScrollLock();

    if (localStorage.getItem('token')) {
        const before = claimStateSignature();
        setVaultRefreshing(true);
        try {
            // Bounded on purpose. Clicking while the page's own start-up
            // /api/user is still in flight can leave the follow-up request
            // unresolved in the browser — the server answers both in under a
            // second, so this is a client-side race, not a slow backend.
            // Without a ceiling the indicator would spin for the rest of the
            // session. The cards are already on screen either way.
            await withTimeout(
                (async () => { await fetchTotalPoints(); await loadRecommendations(); })(),
                VAULT_REFRESH_TIMEOUT
            );
        } catch (err) {
            console.warn('Vault refresh did not complete; showing cached offers.', err);
        } finally {
            setVaultRefreshing(false);
        }
        // Repaint if anything changed, and always on the first open, where
        // there are skeletons standing in for cards that do not exist yet.
        if (claimStateSignature() !== before
            || claimCardsGrid.querySelector('.claim-skeleton')) {
            showClaimCards();
        }
    }
    return;
}

/** Point balance + ranked offer ids — cheap way to tell if a re-render is warranted. */
function claimStateSignature() {
    const ids = (RECOMMENDED_OFFERS || []).map(o => o && o.id).join(',');
    return `${Number(totalPoints) || 0}|${USER_RECEIPTS_SEEN}|${ids}`;
}

/** Render the vault from whatever is currently in memory. */
function showClaimCards() {
    renderClaimCards();
    // Nothing to rank yet (a new account with no receipts). Say so — leaving
    // skeletons up would imply data is still coming when it is not.
    if (claimCardsGrid && !claimCardsGrid.children.length) {
        claimCardsGrid.innerHTML =
            '<p class="vault-empty">Scan a receipt to unlock rewards picked for you.</p>';
    }
    refreshClaimButtonStates();
    claimAvailablePoints.innerText = totalPoints;

    // Wait for modal layout so scratch canvases get the correct size.
    window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
            initScratchCards();
            refreshClaimButtonStates();
        });
    });
}

function closeClaimModal() {
    claimModal.classList.add('hidden');
    syncBodyScrollLock();
}

async function openClaimedModal() {
    if (!localStorage.getItem('token') && currentUserName !== 'Guest Explorer') {
        openAuthModal(true);
        return;
    }

    // Same fault the vault had: this awaited the fetch before opening, so the
    // click sat on a dead page — and the #claimed-loading notice the markup
    // already provides was useless, because it lived inside a modal that had
    // not been shown yet. Open first, then load against skeleton rows.
    //
    // Unlike the vault there is nothing cached to paint: claimed history exists
    // only on the server, so placeholders are the honest first frame.
    showClaimedSkeletons();
    claimedModal.classList.remove('hidden');
    syncBodyScrollLock();

    try {
        await withTimeout(loadClaimedHistory(), VAULT_REFRESH_TIMEOUT);
    } catch (err) {
        // Never leave the placeholders up forever — say what happened instead.
        console.warn('Claimed history did not load.', err);
        clearClaimedSkeletons();
        if (!claimedTableBody.children.length) {
            claimedLoading.style.display = 'none';
            claimedEmpty.style.display = 'block';
            claimedEmpty.textContent =
                'Could not load your claimed vouchers. Please close this and try again.';
        }
    }
}

/** Placeholder rows for the claimed-history table while it loads. */
function showClaimedSkeletons(rows = 4) {
    if (!claimedTableBody) return;
    claimedLoading.style.display = 'none';   // superseded by the rows themselves
    claimedEmpty.style.display = 'none';
    claimedTableBody.innerHTML = Array.from({ length: rows }, () => `
        <tr class="claimed-skeleton-row" aria-hidden="true">
            <td><span class="claim-skeleton__line" style="width:80%"></span></td>
            <td><span class="claim-skeleton__line" style="width:55%"></span></td>
            <td><span class="claim-skeleton__line" style="width:70%"></span></td>
            <td><span class="claim-skeleton__line" style="width:65%"></span></td>
            <td><span class="claim-skeleton__line" style="width:40%;margin-left:auto"></span></td>
        </tr>`).join('');
}

function clearClaimedSkeletons() {
    if (!claimedTableBody) return;
    claimedTableBody.querySelectorAll('.claimed-skeleton-row').forEach(r => r.remove());
}

function closeClaimedModal() {
    claimedModal.classList.add('hidden');
    syncBodyScrollLock();
}

function closeClaimSuccessModal() {
    claimSuccessModal.classList.add('hidden');
    syncBodyScrollLock();
}

function openDigitalBillModal(billData) {
    if (!billData) return;
    billMerchant.innerText = billData.merchant || 'Unknown Merchant';
    billDate.innerText = billData.date || '-';
    billCategory.innerText = billData.category || 'General';
    billTotal.innerText = formatCurrency(Number(billData.total || 0));
    billRefCode.innerText = billData.reference || '-';

    const items = Array.isArray(billData.items) ? billData.items : [];
    if (items.length) {
        billItemsBody.innerHTML = items.map((item) => `
            <tr>
                <td>${item.name || 'Item'}</td>
                <td style="text-align:right;">${item.price != null ? formatCurrency(Number(item.price) || 0) : '-'}</td>
            </tr>
        `).join('');
    } else {
        billItemsBody.innerHTML = '<tr class="empty-row"><td colspan="2">No line items available for this receipt.</td></tr>';
    }

    digitalBillModal.classList.remove('hidden');
    syncBodyScrollLock();
}

function closeDigitalBillModal() {
    digitalBillModal.classList.add('hidden');
    syncBodyScrollLock();
}

// --- Analytics Logic ---

async function openAnalyticsModal() {
    if (!localStorage.getItem('token') && currentUserName !== 'Guest Explorer') {
        openAuthModal(true);
        return;
    }
    analyticsModal.classList.remove('hidden');
    syncBodyScrollLock();
    await loadAnalytics();
}

function closeAnalyticsModal() {
    analyticsModal.classList.add('hidden');
    syncBodyScrollLock();
}

async function loadAnalytics() {
    analyticsLoading.classList.remove('hidden');
    analyticsEmpty.classList.add('hidden');
    analyticsContent.classList.add('hidden');

    try {
        let data = { success: false };
        let res = null;
        if (currentUserName === 'Guest Explorer') {
            await new Promise(r => setTimeout(r, 600)); // Simulate delay
            data = {
                success: true,
                hasData: true,
                summary: {
                    totalBills: 12,
                    totalSpend: 15430,
                    avgBillValue: 1285.83,
                    totalPointsEarned: 840,
                    topCategory: 'Supermarket / Grocery',
                    topMerchant: 'Big Bazaar'
                },
                categories: [
                    { name: 'Supermarket / Grocery', percentage: 45 },
                    { name: 'Food & Beverage', percentage: 30 },
                    { name: 'General Retail', percentage: 25 }
                ],
                insights: [
                    { title: 'Consistent Shopper', text: 'You frequently shop at supermarkets!' },
                    { title: 'Morning Coffee', text: 'Most of your food & beverage expenses happen before noon.' }
                ]
            };
        } else {
            res = await fetch('/api/analytics', { headers: getAuthHeaders() });
            data = await res.json();
        }

        if (!data.success) throw new Error(data.error || 'Failed to fetch analytics');

        analyticsLoading.classList.add('hidden');

        if (!data.hasData) {
            analyticsEmpty.classList.remove('hidden');
            return;
        }

        analyticsContent.classList.remove('hidden');
        const s = data.summary;

        // The footnote must not claim the classifier produced these shares when
        // the guest board is fixed sample data. Two different statements,
        // because one of them would be false in the other mode.
        if (analyticsFootnote) {
            analyticsFootnote.innerText = currentUserName === 'Guest Explorer'
                ? 'Demo data. These figures are a fixed sample used to show the layout — '
                  + 'no receipts were analysed and no model produced them.'
                : 'Computed from the receipts on this account. Category shares come from the '
                  + 'trained classifier, not from the merchant name alone.';
        }

        // Numbers
        analyticsTotalBills.innerText = s.totalBills;
        analyticsTotalSpend.innerText = `₹${s.totalSpend.toLocaleString('en-IN')}`;
        analyticsAvgBillValue.innerText = `₹${s.avgBillValue.toLocaleString('en-IN')}`;
        analyticsTotalPoints.innerText = s.totalPointsEarned;
        analyticsTopCategoryLabel.innerText = s.topCategory;
        analyticsTopMerchantLabel.innerText = s.topMerchant;
        analyticsMainInterest.innerText = s.topCategory;

        // Donut drawn as SVG arcs on a 42x42 viewBox: circumference is
        // 2*pi*r with r = 15.9155, i.e. exactly 100 units, so a category's
        // percentage IS its dash length and no conversion is needed.
        //
        // Okabe-Ito, assigned in fixed order and never cycled. A ninth category
        // would repeat a colour, so the tail is folded into "Other" instead.
        const AN_PALETTE = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00'];
        const AN_CIRCUMFERENCE = 100;

        if (data.categories && data.categories.length > 0) {
            let cats = data.categories.slice();
            if (cats.length > AN_PALETTE.length) {
                const keep = cats.slice(0, AN_PALETTE.length - 1);
                const rest = cats.slice(AN_PALETTE.length - 1);
                keep.push({
                    name: 'Other',
                    percentage: rest.reduce((t, c) => t + Number(c.percentage || 0), 0)
                });
                cats = keep;
            }

            const NS = 'http://www.w3.org/2000/svg';
            analyticsCategoryChart.innerHTML = '';

            // Track behind the arcs, so a partial total still reads as a ring.
            const track = document.createElementNS(NS, 'circle');
            track.setAttribute('cx', '21');
            track.setAttribute('cy', '21');
            track.setAttribute('r', '15.9155');
            track.setAttribute('stroke', 'rgba(30,41,59,0.08)');
            analyticsCategoryChart.appendChild(track);

            let offset = 25;   // start at 12 o'clock
            const arcs = cats.map((c, i) => {
                const pct = Math.max(0, Number(c.percentage) || 0);
                const arc = document.createElementNS(NS, 'circle');
                arc.setAttribute('cx', '21');
                arc.setAttribute('cy', '21');
                arc.setAttribute('r', '15.9155');
                arc.setAttribute('stroke', AN_PALETTE[i]);
                // 0.8 shaved off the dash leaves a hairline gap between
                // neighbours so two adjacent slices never read as one.
                arc.setAttribute('stroke-dasharray',
                    `${Math.max(pct - 0.8, 0.4)} ${AN_CIRCUMFERENCE - pct}`);
                arc.setAttribute('stroke-dashoffset', String(offset));
                arc.setAttribute('stroke-linecap', 'butt');
                const title = document.createElementNS(NS, 'title');
                title.textContent = `${c.name}: ${pct}%`;   // native tooltip
                arc.appendChild(title);
                offset -= pct;
                return arc;
            });
            arcs.forEach(a => analyticsCategoryChart.appendChild(a));

            analyticsLegend.innerHTML = cats.map((c, i) => `
                <li data-slice="${i}">
                    <span class="legend-dot" style="background:${AN_PALETTE[i]}"></span>
                    <span class="legend-label">${c.name}</span>
                    <span class="legend-value">${c.percentage}%</span>
                    <span class="legend-bar">
                        <span style="width:${Math.min(100, c.percentage)}%;background:${AN_PALETTE[i]}"></span>
                    </span>
                </li>
            `).join('');

            // Hovering either the slice or its legend row highlights both, so
            // the mapping between them never has to be guessed.
            const rows = [...analyticsLegend.querySelectorAll('li')];
            const link = (i, on) => {
                if (arcs[i]) arcs[i].classList.toggle('is-active', on);
                if (rows[i]) rows[i].classList.toggle('is-active', on);
                analyticsCategoryChart.classList.toggle('is-hovered', on);
            };
            rows.forEach((row, i) => {
                row.addEventListener('mouseenter', () => link(i, true));
                row.addEventListener('mouseleave', () => link(i, false));
            });
            arcs.forEach((arc, i) => {
                arc.addEventListener('mouseenter', () => link(i, true));
                arc.addEventListener('mouseleave', () => link(i, false));
            });
        }

        // Insights
        if (data.insights && data.insights.length > 0) {
            analyticsInsightsList.innerHTML = data.insights.map(ins => `
                <li>
                    <span class="insight-icon" aria-hidden="true">💡</span>
                    <div class="insight-body">
                        <h4>${ins.title}</h4>
                        <p>${ins.text}</p>
                    </div>
                </li>
            `).join('');
        } else {
            analyticsInsightsList.innerHTML =
                '<li><span class="insight-icon" aria-hidden="true">📄</span>'
                + '<div class="insight-body"><h4>Not enough history yet</h4>'
                + '<p>Scan a few more receipts and patterns will appear here.</p></div></li>';
        }

    } catch (err) {
        console.error(err);
        analyticsLoading.innerText = "Error loading analytics. Please try again.";
    }
}

// --- Error Modal Logic ---

/** Shown once on entering guest mode — see the note at the call site. */
function openGuestDisclaimer() {
    openErrorModal(
        'Guest Mode — Demo Data Only',
        'You are exploring the interface with mock data.\n\n'
        + '• No receipt is sent to the AI — the Gemini OCR call is skipped entirely\n'
        + '• No trained model runs — category, fraud, anomaly and recommendation '
        + 'results are placeholders, not predictions\n'
        + '• Nothing is saved — points, vouchers and claim codes are generated in '
        + 'your browser and disappear on refresh\n\n'
        + 'Sign up for a free account to run the real pipeline end to end.\n\n'
        + '— Team ARAJ',
        '🎭'
    );
}

function openErrorModal(title = "Error", message = "An error occurred.", icon = "⚠️") {
    if (errorModalIcon) errorModalIcon.innerText = icon;
    if (errorModalTitle) errorModalTitle.innerText = title;
    if (errorModalMessage) errorModalMessage.innerText = message;
    errorModal.classList.remove('hidden');
    syncBodyScrollLock();
}

function closeErrorModal() {
    errorModal.classList.add('hidden');
    syncBodyScrollLock();
}

function playPartyAnimation() {
    if (!partyStage) return;
    partyStage.innerHTML = '';
    const palette = ['#22c55e', '#f59e0b', '#0ea5e9', '#ef4444', '#a855f7', '#14b8a6'];

    for (let i = 0; i < 28; i += 1) {
        const confetti = document.createElement('span');
        confetti.className = 'party-confetti';
        confetti.style.left = `${Math.random() * 100}%`;
        confetti.style.background = palette[Math.floor(Math.random() * palette.length)];
        confetti.style.animationDelay = `${Math.random() * 220}ms`;
        confetti.style.setProperty('--shift-x', `${(Math.random() - 0.5) * 130}px`);
        partyStage.appendChild(confetti);
    }
}

function openClaimSuccessModal(claimCode, remainingPoints) {
    claimCodeValue.innerText = claimCode;
    claimSuccessPoints.innerText = remainingPoints;
    btnCopyClaimCode.innerText = 'Copy Code';
    claimSuccessModal.classList.remove('hidden');
    syncBodyScrollLock();
    playPartyAnimation();
}

function random12DigitCode() {
    let code = '';
    for (let i = 0; i < 12; i += 1) {
        code += Math.floor(Math.random() * 10);
    }
    return code;
}

async function copyTextToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (_err) {
        try {
            const temp = document.createElement('textarea');
            temp.value = text;
            document.body.appendChild(temp);
            temp.select();
            document.execCommand('copy');
            temp.remove();
            return true;
        } catch (_fallbackErr) {
            return false;
        }
    }
}

async function copyClaimCode() {
    const text = String(claimCodeValue.innerText || '').replace(/\s+/g, '');
    const copied = await copyTextToClipboard(text);
    btnCopyClaimCode.innerText = copied ? 'Copied!' : 'Copy Failed';
    if (claimCodeCopyTimer) clearTimeout(claimCodeCopyTimer);
    claimCodeCopyTimer = setTimeout(() => {
        btnCopyClaimCode.innerText = 'Copy Code';
    }, 1300);
}

function refreshClaimButtonStates() {
    const available = Number(totalPoints) || 0;
    claimCardsGrid.querySelectorAll('.claim-card').forEach(card => {
        if (card.dataset.claimed === 'true') return;
        const required = Number.parseInt(card.dataset.requiredPoints || '0', 10);
        const button = card.querySelector('[data-voucher-btn], [data-scratch-btn]');
        if (!button) return;

        const hasPoints = available >= required;
        const isScratch = card.dataset.type === 'scratch';
        const isScratched = card.dataset.scratched === 'true';
        const canClaim = isScratch ? (hasPoints && isScratched) : hasPoints;

        button.disabled = !canClaim;
        if (isScratch) {
            if (!hasPoints) {
                button.innerText = `Need ${required} pts`;
            } else if (!isScratched) {
                button.innerText = 'Scratch to Unlock';
            } else {
                button.innerText = 'Claim Scratch Card';
            }
        } else {
            button.innerText = hasPoints ? 'Claim Voucher' : `Need ${required} pts`;
        }

        // Keep scratch cards interactive when points are available, even before reveal.
        card.classList.toggle('claim-card--locked', !hasPoints);
    });
}

async function claimRewardFromCard(card, buttonEl) {
    if (!card || !buttonEl || card.dataset.claimed === 'true') return;
    if (card.dataset.type === 'scratch' && card.dataset.scratched !== 'true') {
        alert('Scratch the card first to reveal and unlock this reward.');
        return;
    }
    const requiredPoints = Number.parseInt(card.dataset.requiredPoints || '0', 10);
    if (!Number.isInteger(requiredPoints) || requiredPoints <= 0) return;

    const payload = {
        type: card.dataset.type || 'voucher',
        title: card.dataset.title || 'Reward',
        offer: card.dataset.offer || '',
        reward: card.dataset.reward || '',
        requiredPoints,
        code: random12DigitCode()
    };

    // Claiming is a network round trip plus an atomic Firestore transaction, so
    // the wait is real. Capture innerHTML rather than innerText — the restore
    // path has to put back exactly what was there, spinner markup included.
    const originalHTML = buttonEl.innerHTML;
    const restoreButton = () => {
        buttonEl.disabled = false;
        buttonEl.classList.remove('is-busy');
        buttonEl.innerHTML = originalHTML;
    };
    buttonEl.disabled = true;
    buttonEl.classList.add('is-busy');
    buttonEl.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>Claiming...';

    try {
        let data = {};
        if (currentUserName === 'Guest Explorer') {
            await new Promise(r => setTimeout(r, 800)); // Simulate delay
            data = {
                success: true,
                remainingPoints: totalPoints - payload.requiredPoints,
                claim: {
                    claim_code: payload.code
                }
            };
        } else {
            const response = await fetch('/api/claim-reward', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(payload)
            });

            if (response.status === 401 || response.status === 403) {
                // Restore before bailing — the session may be restored behind
                // this modal, and a button left mid-spin never recovers.
                restoreButton();
                localStorage.removeItem('token');
                checkAuth();
                return;
            }

            data = await response.json();
            if (!response.ok || !data.success) {
                restoreButton();
                alert(data.error || 'Unable to claim reward right now.');
                return;
            }
        }

        const remaining = Number(data.remainingPoints) || 0;
        totalPoints = remaining;
        totalPointsDisplay.innerText = remaining;
        claimAvailablePoints.innerText = remaining;

        card.dataset.claimed = 'true';
        card.classList.add('claim-card--locked');
        buttonEl.classList.remove('is-busy');
        buttonEl.innerText = 'Claimed';
        buttonEl.disabled = true;

        // For guest, add to mock history array locally if we wanted to be perfectly persistent for the session. For simplicity and since fetch overrides, let's just show success

        if (payload.type === 'scratch') {
            card.dataset.scratched = 'true';
            card.classList.add('is-scratched');
            const canvas = card.querySelector('.scratch-canvas');
            if (canvas) canvas.classList.add('is-cleared');
        }

        refreshClaimButtonStates();
        openClaimSuccessModal(data.claim?.claim_code || payload.code, remaining);

        if (!claimedModal.classList.contains('hidden')) {
            loadClaimedHistory();
        }
    } catch (error) {
        console.error('Claim error:', error);
        restoreButton();
        alert('Network error while claiming reward.');
    }
}

// ── AUTH STATE MANAGEMENT ──────────────────────────────────────
// Checks localStorage for a JWT; shows app or landing page accordingly
function checkAuth() {
    const token = localStorage.getItem('token');
    if (token || currentUserName === 'Guest Explorer') {
        sectionAuth.classList.add('hidden');
        appContent.classList.remove('hidden');
        btnLogout.classList.remove('hidden');
        btnTry.classList.add('hidden');
        if (btnGuest) btnGuest.classList.add('hidden');
        closeAuthModal();
        claimAvailablePoints.innerText = totalPoints;
        if (token) fetchTotalPoints();
        // The scanner is now on screen, so the consent gate is due.
        openConsentGateIfDue();
    } else {
        sectionAuth.classList.remove('hidden');
        appContent.classList.add('hidden');
        btnLogout.classList.add('hidden');
        btnTry.classList.remove('hidden');
        if (btnGuest) btnGuest.classList.remove('hidden');
        currentUserName = 'User';
        closeClaimModal();
        closeClaimSuccessModal();
        closeDigitalBillModal();
        closeClaimedModal();
        closeAnalyticsModal();
        closeErrorModal();
        if (welcomeIntro) welcomeIntro.classList.add('hidden');
    }
}

// ── INITIALISATION ─────────────────────────────────────────────
// On page load: check auth state and start hero typing animation
document.addEventListener('DOMContentLoaded', () => {
    // initConsentGate() first: it wires Accept/Decline, and checkAuth() can open
    // the gate immediately for an already-signed-in user.
    initConsentGate();
    initTermsAgreement();
    checkAuth();
    startHeroTyping();
    initCarousels();
});

// ── MOBILE SWIPE CAROUSELS ─────────────────────────────────────
// On phones the Learn More / How It Works / Under the Hood card groups turn
// into one-card-per-view horizontal carousels (styling lives in the CSS).
// This adds pagination dots and keeps the active dot in sync with the swipe,
// so the sections take far less vertical space without cramping the cards.
function initCarousels() {
    const groups = [
        { track: document.querySelector('.landing-features'), slide: '.landing-feature' },
        { track: document.querySelector('.landing-section .hero-content'), slide: '.hero-block' },
        { track: document.querySelector('.hiw-pipeline'), slide: '.hiw-stage' },
        { track: document.querySelector('.hiw-arch-grid'), slide: '.hiw-arch-card' },
    ];

    groups.forEach(({ track, slide }) => {
        if (!track) return;
        const slides = track.querySelectorAll(slide);
        if (slides.length < 2) return;

        // Build the dots
        const dots = document.createElement('div');
        dots.className = 'carousel-dots';
        slides.forEach((s, i) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.setAttribute('aria-label', 'Show item ' + (i + 1));
            if (i === 0) b.classList.add('active');
            b.addEventListener('click', () => {
                s.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            });
            dots.appendChild(b);
        });
        track.insertAdjacentElement('afterend', dots);

        // Keep the active dot in sync as the user swipes
        const buttons = dots.querySelectorAll('button');
        let raf = null;
        track.addEventListener('scroll', () => {
            if (raf) cancelAnimationFrame(raf);
            raf = requestAnimationFrame(() => {
                const cRect = track.getBoundingClientRect();
                const center = cRect.left + cRect.width / 2;
                let best = 0, bestDist = Infinity;
                slides.forEach((s, i) => {
                    const r = s.getBoundingClientRect();
                    const dist = Math.abs((r.left + r.width / 2) - center);
                    if (dist < bestDist) { bestDist = dist; best = i; }
                });
                buttons.forEach((d, i) => d.classList.toggle('active', i === best));
            });
        }, { passive: true });
    });
}

// ── DATA CONSENT / TERMS & CONDITIONS GATE ─────────────────────
// Simple educational consent flow: on first visit, ask the user to accept
// how their receipt data is handled. Choice is stored in localStorage so it
// only appears once. Frontend-only — no backend wiring.
const CONSENT_KEY = 'dataConsentAccepted';

function hasDataConsent() {
    return localStorage.getItem(CONSENT_KEY) === 'true';
}

// Opens the first-visit gate, but only once there is a scanner to gate.
//
// The modal used to sit inside #app-content, which is hidden until login — so
// although this ran on DOMContentLoaded, nothing appeared until the user signed
// in and that wrapper was revealed. Moving the modal to body level (so the
// sign-up and footer links can reach it) removed that accidental timing, and
// without this check a logged-out visitor would be met by a consent wall whose
// only exits are Accept or a scolding. Called again from checkAuth() when the
// app is revealed, which is when the original behaviour actually kicked in.
function openConsentGateIfDue() {
    const modal = document.getElementById('consent-modal');
    if (!modal || hasDataConsent()) return;
    if (!appContent || appContent.classList.contains('hidden')) return;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
}

function initConsentGate() {
    const modal = document.getElementById('consent-modal');
    if (!modal) return;

    const checkbox = document.getElementById('consent-checkbox');
    const acceptBtn = document.getElementById('consent-accept');
    const declineBtn = document.getElementById('consent-decline');
    const declinedMsg = document.getElementById('consent-declined-msg');

    // Already consented → never show again
    if (hasDataConsent()) return;

    const openModal = () => {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    };
    const closeModal = () => {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    };

    // Accept button enables only once the checkbox is ticked
    if (checkbox && acceptBtn) {
        checkbox.addEventListener('change', () => {
            acceptBtn.disabled = !checkbox.checked;
            if (checkbox.checked && declinedMsg) declinedMsg.classList.add('hidden');
        });
    }

    if (acceptBtn) {
        acceptBtn.addEventListener('click', () => {
            if (!checkbox || !checkbox.checked) return;
            localStorage.setItem(CONSENT_KEY, 'true');
            closeModal();
        });
    }

    if (declineBtn) {
        declineBtn.addEventListener('click', () => {
            // Educational: consent is required to proceed — keep the gate up.
            if (declinedMsg) declinedMsg.classList.remove('hidden');
        });
    }

    openConsentGateIfDue();
}

// Re-open the terms for READING — from the footer link, or the sign-up checkbox.
//
// Distinct from the first-visit gate above. That one demands a decision and has no
// way out but Accept; this is someone who wants to re-read what they agreed to, so
// it swaps the Accept/Decline pair for a plain Close. Without that swap a visitor
// who had already consented could open the terms and be trapped — Accept is
// disabled until the checkbox is ticked, and Decline only scolds them.
function showConsentTerms() {
    const modal = document.getElementById('consent-modal');
    if (!modal) return;

    const actions = modal.querySelector('.consent-actions');
    const check = modal.querySelector('.consent-check');
    const declined = document.getElementById('consent-declined-msg');

    const close = () => {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        if (actions) actions.innerHTML = actionsHtml;
        if (check) check.classList.remove('hidden');
        document.removeEventListener('keydown', onKey);
    };
    const onKey = (e) => { if (e.key === 'Escape') close(); };

    // Reading mode: the tick-to-accept row is irrelevant, and one button is enough.
    const actionsHtml = actions ? actions.innerHTML : '';
    if (check) check.classList.add('hidden');
    if (declined) declined.classList.add('hidden');
    if (actions) {
        actions.innerHTML = '<button class="btn btn-primary" type="button">Close</button>';
        actions.querySelector('button').addEventListener('click', close);
    }
    modal.querySelectorAll('.consent-modal-backdrop').forEach(b => b.addEventListener('click', close));
    document.addEventListener('keydown', onKey);

    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    const scroller = document.getElementById('consent-terms');
    if (scroller) { scroller.scrollTop = 0; scroller.focus(); }
}
window.showConsentTerms = showConsentTerms;

// ── SIGN-UP TERMS AGREEMENT ────────────────────────────────────
// The scanner already gates on consent, but that gate fires on first visit and is
// tied to the browser, not the account. Agreeing at sign-up records the decision
// where the account is actually created, which is what the report's privacy
// section describes. Sign-up only — asking an existing user to re-agree on every
// login would be noise.
function initTermsAgreement() {
    const box = document.getElementById('auth-terms-checkbox');
    const formLink = document.getElementById('auth-terms-link');
    const footLink = document.getElementById('footer-terms-link');

    [formLink, footLink].forEach(link => {
        if (!link) return;
        link.addEventListener('click', (e) => {
            e.preventDefault();
            // Don't let a click on the link toggle the checkbox it sits inside.
            e.stopPropagation();
            showConsentTerms();
        });
    });

    // Ticking it clears any "you must agree" error still on screen.
    if (box) {
        box.addEventListener('change', () => {
            if (box.checked && authError && authError.innerText === TERMS_REQUIRED_MSG) {
                authError.classList.add('hidden');
            }
        });
    }
}

function startHeroTyping() {
    if (!heroTypingTitle) return;
    // If a non-English language is active, i18n sets the title directly — skip typing.
    try {
        const savedLang = localStorage.getItem('lang');
        if (savedLang && savedLang !== 'en') return;
    } catch (e) { }

    const fullText = heroTypingTitle.dataset.typingText || heroTypingTitle.innerText || "";
    heroTypingTitle.classList.add('typing-active');
    heroTypingTitle.textContent = "";

    let index = 0;
    const typeNext = () => {
        if (index >= fullText.length) {
            setTimeout(() => heroTypingTitle.classList.remove('typing-active'), 650);
            return;
        }

        const char = fullText.charAt(index);
        if (char === '|') {
            heroTypingTitle.insertAdjacentHTML('beforeend', '<br class="mobile-break">');
        } else {
            heroTypingTitle.insertAdjacentText('beforeend', char === ' ' ? '\u00A0' : char);
        }
        index += 1;

        const delay = char === ' ' ? 45 : 45 + Math.floor(Math.random() * 70);
        setTimeout(typeNext, delay);
    };

    typeNext();
}

// ── AUTH MODAL & FORM ──────────────────────────────────────────
// Handles login/signup form toggle, form submit, and JWT storage

const TERMS_REQUIRED_MSG = 'Please agree to the Terms & Data Policy to create an account.';

function setAuthMode(loginMode) {
    isLoginMode = loginMode;
    const termsGroup = document.getElementById('auth-terms-group');
    const termsBox = document.getElementById('auth-terms-checkbox');
    if (isLoginMode) {
        authTitle.innerText = "Login to Account";
        authSubtitle.innerText = "Access your reward dashboard";
        authNameGroup.classList.add('hidden');
        authSubmitBtn.innerText = "Login";
        authSwitchText.innerText = "Don't have an account?";
        authSwitchLink.innerText = "Sign up";
        authName.required = false;
    } else {
        authTitle.innerText = "Create Account";
        authSubtitle.innerText = "Join the rewards program";
        authNameGroup.classList.remove('hidden');
        authSubmitBtn.innerText = "Sign Up";
        authSwitchText.innerText = "You have account?";
        authSwitchLink.innerText = "Sign in";
        authName.required = true;
    }
    // Agreement belongs to account creation, not to signing in again. Reset on
    // every switch so a tick left over from an abandoned sign-up cannot carry.
    if (termsGroup) termsGroup.classList.toggle('hidden', isLoginMode);
    if (termsBox) termsBox.checked = false;
    authError.classList.add('hidden');
}

function playAuthModalIntro() {
    if (!authModal) return;
    authModal.classList.remove('auth-intro-active');
    void authModal.offsetWidth;
    authModal.classList.add('auth-intro-active');
    window.setTimeout(() => {
        authModal.classList.remove('auth-intro-active');
    }, 620);
}

function playWelcomeIntro(name = 'User', options = {}) {
    if (!welcomeIntro || !welcomeIntroText) return Promise.resolve();

    const normalizedName = String(name || 'User').trim() || 'User';
    const fallbackMessage = `Welcome ${normalizedName} !`;
    const message = String(options.message || fallbackMessage).trim() || fallbackMessage;
    const kicker = String(options.kicker || 'Access Granted').trim() || 'Access Granted';
    const durationMs = Number.parseInt(options.durationMs, 10) > 0 ? Number.parseInt(options.durationMs, 10) : 1700;

    if (welcomeIntroKicker) {
        welcomeIntroKicker.innerText = kicker;
    }
    welcomeIntroText.innerText = message;
    welcomeIntro.classList.remove('hidden', 'welcome-intro-active');
    void welcomeIntro.offsetWidth;
    welcomeIntro.classList.add('welcome-intro-active');
    syncBodyScrollLock();

    return new Promise((resolve) => {
        window.setTimeout(() => {
            welcomeIntro.classList.add('hidden');
            welcomeIntro.classList.remove('welcome-intro-active');
            syncBodyScrollLock();
            resolve();
        }, durationMs);
    });
}

function openAuthModal(signupByDefault = true) {
    setAuthMode(!signupByDefault);
    authModal.classList.remove('hidden');
    syncBodyScrollLock();
    playAuthModalIntro();
}

function closeAuthModal() {
    authModal.classList.add('hidden');
    syncBodyScrollLock();
}

btnTry.addEventListener('click', () => openAuthModal(true));
if (btnGuest) {
    btnGuest.addEventListener('click', async () => {
        currentUserName = 'Guest Explorer';
        sectionAuth.classList.add('hidden');
        appContent.classList.remove('hidden');
        btnLogout.classList.remove('hidden');
        btnTry.classList.add('hidden');
        btnGuest.classList.add('hidden');
        closeAuthModal();
        // Reveals the scanner without going through checkAuth(), so the gate
        // has to be prompted here too.
        openConsentGateIfDue();

        // Give guest some points to explore the reward UI
        totalPoints = 500;
        totalPointsDisplay.innerText = totalPoints;
        claimAvailablePoints.innerText = totalPoints;

        await playWelcomeIntro('Guest Explorer');
        appContent.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Guest mode is a UI walkthrough, not the system. Nothing here touches
        // Gemini, the trained models or Firestore — the points, offers and
        // claim codes are all local fixtures. Saying so up front matters: a
        // panel member clicking "Try as Guest" would otherwise see numbers that
        // look like model output and reasonably assume they are.
        openGuestDisclaimer();
    });
}
authModalClose.addEventListener('click', closeAuthModal);
authModalBackdrop.addEventListener('click', closeAuthModal);
btnClaimPoints.addEventListener('click', openClaimModal);
btnViewClaimed.addEventListener('click', openClaimedModal);
btnViewDigitalBill.addEventListener('click', () => openDigitalBillModal(latestProcessedBillData));
claimModalClose.addEventListener('click', closeClaimModal);
claimModalBackdrop.addEventListener('click', closeClaimModal);
claimedModalClose.addEventListener('click', closeClaimedModal);
claimedModalBackdrop.addEventListener('click', closeClaimedModal);
claimSuccessClose.addEventListener('click', closeClaimSuccessModal);
claimSuccessBackdrop.addEventListener('click', closeClaimSuccessModal);
digitalBillClose.addEventListener('click', closeDigitalBillModal);
digitalBillBackdrop.addEventListener('click', closeDigitalBillModal);
btnViewAnalytics.addEventListener('click', openAnalyticsModal);
analyticsModalClose.addEventListener('click', closeAnalyticsModal);
analyticsModalBackdrop.addEventListener('click', closeAnalyticsModal);
errorModalClose.addEventListener('click', closeErrorModal);
errorModalBackdrop.addEventListener('click', closeErrorModal);
btnErrorOk.addEventListener('click', closeErrorModal);
btnCopyClaimCode.addEventListener('click', copyClaimCode);
if (btnOpenClaimedFromClaim) {
    btnOpenClaimedFromClaim.addEventListener('click', async () => {
        closeClaimModal();
        await openClaimedModal();
    });
}
if (btnOpenClaimFromClaimed) {
    btnOpenClaimFromClaimed.addEventListener('click', async () => {
        closeClaimedModal();
        await openClaimModal();
    });
}
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (!digitalBillModal.classList.contains('hidden')) {
        closeDigitalBillModal();
        return;
    }
    if (!claimSuccessModal.classList.contains('hidden')) {
        closeClaimSuccessModal();
        return;
    }
    if (!claimedModal.classList.contains('hidden')) {
        closeClaimedModal();
        return;
    }
    if (!claimModal.classList.contains('hidden')) {
        closeClaimModal();
        return;
    }
    if (!analyticsModal.classList.contains('hidden')) {
        closeAnalyticsModal();
        return;
    }
    if (!errorModal.classList.contains('hidden')) {
        closeErrorModal();
        return;
    }
    if (!authModal.classList.contains('hidden')) {
        closeAuthModal();
    }
});

authSwitchLink.addEventListener('click', (e) => {
    e.preventDefault();
    setAuthMode(!isLoginMode);
});

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    authError.classList.add('hidden');

    // Checked before the button is disabled, so a refusal leaves the form usable.
    // Not `required` on the input: the native bubble is easy to miss on a dark
    // panel, and this reuses the error line the rest of the form already speaks
    // through.
    const termsBox = document.getElementById('auth-terms-checkbox');
    if (!isLoginMode && termsBox && !termsBox.checked) {
        authError.innerText = TERMS_REQUIRED_MSG;
        authError.classList.remove('hidden');
        termsBox.focus();
        return;
    }

    authSubmitBtn.disabled = true;
    authSubmitBtn.innerText = "Processing...";

    const endpoint = isLoginMode ? '/api/login' : '/api/signup';
    const payload = {
        email: authEmail.value,
        password: authPassword.value,
        name: authName.value
    };

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok && data.token) {
            const welcomeName = String(data.name || authName.value || 'User').trim() || 'User';
            currentUserName = welcomeName;
            localStorage.setItem('token', data.token);
            authEmail.value = "";
            authPassword.value = "";
            authName.value = "";
            resetUI();
            closeAuthModal();
            closeClaimModal();
            closeClaimSuccessModal();
            closeDigitalBillModal();
            checkAuth();
            await playWelcomeIntro(welcomeName);
            appContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            authError.innerText = data.error || "Authentication failed.";
            authError.classList.remove('hidden');
        }
    } catch (err) {
        authError.innerText = "Network Error.";
        console.error(err);
        authError.classList.remove('hidden');
    } finally {
        authSubmitBtn.disabled = false;
        authSubmitBtn.innerText = isLoginMode ? "Login" : "Sign Up";
    }
});

btnLogout.addEventListener('click', async () => {
    const farewellName = String(currentUserName || 'User').trim() || 'User';
    await playWelcomeIntro(farewellName, {
        kicker: 'Logout Successful',
        message: `See you soon ${farewellName} 🙂`,
        durationMs: 1450
    });

    localStorage.removeItem('token');
    currentUserName = 'User';
    totalPoints = 0;
    totalPointsDisplay.innerText = "0";
    historyTableBody.innerHTML = "";
    valRawMerchant.innerText = '--';
    valDate.innerText = '--';
    valTotal.innerText = '--';
    valItems.innerHTML = '';
    valCategory.innerText = '--';
    clearVerification();
    valEarnedPoints.innerText = '0';
    valRewardLogic.innerText = '--';
    resetUI();
    closeAuthModal();
    closeClaimModal();
    closeClaimSuccessModal();
    closeDigitalBillModal();
    checkAuth();
});

// ── POINTS SYNC ────────────────────────────────────────────────
// Fetches live point balance from /api/user and updates all displays
async function fetchTotalPoints() {
    try {
        const response = await fetch('/api/user', { headers: getAuthHeaders() });
        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem('token');
            checkAuth();
            return null;
        }
        const data = await response.json();
        if (data && data.totalPoints !== undefined) {
            totalPoints = Number(data.totalPoints) || 0;
            totalPointsDisplay.innerText = totalPoints;
            claimAvailablePoints.innerText = totalPoints;
            currentUserName = String(data.name || currentUserName || 'User').trim() || 'User';
        }
        return totalPoints;
    } catch (error) {
        console.error("Error fetching user data:", error);
        return null;
    }
}

// ── STEPPER & STAGE HELPERS ────────────────────────────────────

// Advances the 4-step progress bar (Upload → Extract → Process → Reward)
function activateStep(stepEl) {
    const nextIndex = STEP_SEQUENCE.indexOf(stepEl);
    if (nextIndex === -1) return;

    STEP_SEQUENCE.forEach((el, idx) => {
        el.classList.remove('active', 'completed', 'step-enter', 'step-pulse');
        if (idx < nextIndex) {
            el.classList.add('completed');
        }
    });

    stepEl.classList.add('active');

    // Handle Arrows
    const arrows = document.querySelectorAll('.step-transition-arrow');
    arrows.forEach((arrow, idx) => {
        arrow.classList.remove('completed', 'animating');
        if (idx < nextIndex - 1) {
            arrow.classList.add('completed');
        } else if (idx === nextIndex - 1) {
            arrow.classList.add('animating');
        }
    });

    // Step transition animation: pulse previous step + enter animation on next step.
    if (nextIndex !== currentStepIndex) {
        const prevStep = STEP_SEQUENCE[currentStepIndex];
        if (prevStep && nextIndex > currentStepIndex) {
            void prevStep.offsetWidth;
            prevStep.classList.add('step-pulse');
            window.setTimeout(() => {
                prevStep.classList.remove('step-pulse');
            }, 430);
        }

        void stepEl.offsetWidth;
        stepEl.classList.add('step-enter');
    }

    currentStepIndex = nextIndex;
}

function showStage(stageEl) {
    [stageUpload, stageExtracting, stageResults].forEach(el => el.classList.add('hidden'));
    stageEl.classList.remove('hidden');
}

// Format currency
const formatCurrency = (amount) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);

// ── RECEIPT UPLOAD PIPELINE ────────────────────────────────────
// File input / drag-drop → base64 encode → POST /api/upload → show results

// 1. Upload Handler — wires file input and drag-and-drop zone to handleUpload()
fileInput.addEventListener('change', handleUpload);
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleUpload();
    }
});

async function handleUpload() {
    if (!fileInput.files.length) return;

    // Move to Extract step
    activateStep(stepExtract);
    showStage(stageExtracting);

    startOcrProgress();

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = async (e) => {
        const base64String = e.target.result.split(',')[1];

        try {
            let status = 200;
            let result = {};

            if (currentUserName === 'Guest Explorer') {
                await new Promise(r => setTimeout(r, 2500)); // Simulate processing delay
                result = {
                    success: true,
                    data: {
                        rawMerchant: 'Demo Supermarket',
                        date: new Date().toLocaleDateString(),
                        total: 1250,
                        category: 'Supermarket / Grocery',
                        rewardPoints: 50,
                        rewardLogic: 'Base points (1%) + Grocery Bonus (5 pts)',
                        receiptId: `MOCK-${Date.now()}`,
                        items: [
                            { name: 'Apples 1kg', price: '120.00' },
                            { name: 'Milk 1L', price: '60.00' },
                            { name: 'Bread', price: '45.00' },
                            { name: 'Demo Item 4', price: '1025.00' }
                        ]
                    }
                };
            } else {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({
                        receipt: base64String,
                        mimeType: file.type
                    })
                });

                status = response.status;
                try {
                    result = await response.json();
                } catch (jsonErr) {
                    console.warn('Backend did not return valid JSON:', jsonErr);
                }
            }

            if (status === 200 && result.success) {
                stopOcrProgress(true);

                setTimeout(() => {
                    processReceiptData(result.data);
                }, 500);
            } else if (status === 409) {
                stopOcrProgress();
                // A bill claimed on someone else's account is not the user's
                // fault, and the person seeing this may well be the rightful
                // owner. Keep that case calm — the warning triangle reads as an
                // accusation, which is wrong for a message we cannot be certain
                // about. Re-uploading your own receipt stays a plain warning.
                if (result.code === 'ALREADY_CLAIMED') {
                    openErrorModal('Already Claimed', result.error, '🧾');
                } else if (result.code === 'DUPLICATE_IMAGE') {
                    // The perceptual-hash match: the same bill photographed a
                    // second time. Different bytes, so the fingerprint check
                    // above let it through. Same picture, so no second reward.
                    // Kept as calm as ALREADY_CLAIMED — it is usually the same
                    // person re-uploading, not an attempt to cheat.
                    openErrorModal('Receipt Already Submitted', result.error, '🧾');
                } else {
                    openErrorModal('Duplicate Receipt Detected', result.error || 'This receipt has already been processed.', '⚠️');
                }
                resetUI();
            } else if (status === 422) {
                stopOcrProgress();
                // Title the dialog after the actual problem. Every rejection used
                // to open as "Scan Failed" above the words "Scan Failed: Please
                // ensure the receipt is clear." — the phrase twice, and no idea
                // what to do differently. The backend now says which case it is.
                const OCR_FAILURES = {
                    IMAGE_TOO_BLURRY: { title: 'Photo Too Blurry', icon: '📷' },
                    MULTI_BILL:       { title: 'More Than One Receipt', icon: '🧾' },
                    UNREADABLE:       { title: "Couldn't Read This Receipt", icon: '🔍' }
                };
                const failure = OCR_FAILURES[result.code] || OCR_FAILURES.UNREADABLE;
                openErrorModal(
                    failure.title,
                    result.error || 'We could not read this image. Please try another photo of the bill.',
                    failure.icon
                );
                resetUI();
            } else if (status === 429) {
                stopOcrProgress();
                openErrorModal('Rate Limit Exceeded', result.error || 'The AI service is currently busy. Please try again in a few moments.', '⏳');
                resetUI();
            } else {
                stopOcrProgress();
                openErrorModal('Processing Error', 'Error processing receipt: ' + (result.error || `HTTP Status ${status}`), '📡');
                resetUI();
            }
        } catch (error) {
            console.error('Upload Error:', error);
            stopOcrProgress();
            openErrorModal('Network Error', 'A network error occurred while processing the receipt. Please check your connection.', '🌐');
            resetUI();
        }
    };

    reader.onerror = () => {
        alert("Error reading file");
        resetUI();
    };

    reader.readAsDataURL(file);
}

// 2. Process Data — populates result fields and advances to Reward step
// Clears the verification block so one receipt's verdict never bleeds into the
// next scan.
function clearVerification() {
    valRisk.innerText = '--';
    valRisk.className = 'risk-badge';
    valFraudScore.innerText = '--';
    valFraudScore.classList.remove('is-flagged');
    valAnomaly.innerText = '--';
    valAnomaly.classList.remove('is-flagged');
    verifyNote.innerText = '';
    verificationDetail.hidden = true;
}

// ── OCR PROGRESS ───────────────────────────────────────────────
// The extraction wait is long and variable: ocr.py holds a 23-second rate-limit
// gate before it may call Gemini at all, and on a transient failure it retries
// up to three times per model across two models. A worst case runs past a
// minute. The old bar eased to 90% over ten seconds and then sat there, so
// every slow extraction looked like a hang.
//
// There is no progress signal to report — the request is one blocking call — so
// the percentage is an ESTIMATE against expected duration, not a measurement.
// It is kept honest three ways: it rises on a curve that never stalls and never
// reaches 100% until the response actually lands; the elapsed counter beside it
// is measured, so something factual is always moving; and the caption names the
// phase the pipeline is genuinely in at that point.
let _ocrTimer = null;
let _ocrStart = 0;

// Time constant of the curve: pct = CEILING * (1 - e^(-t/TAU)).
// ~33% at 8s, ~63% at 20s, ~86% at 40s, ~94% at 60s — always climbing,
// never arriving. ocr.py bounds the attempt at 70s; the curve is paced to that. CEILING leaves headroom so the jump to 100% reads as completion.
const OCR_TAU = 26;   // tuned to the 90s server-side deadline
const OCR_CEILING = 97;

function _ocrPhase(seconds) {
    if (seconds < 2)  return ['Checking image quality…', false];
    if (seconds < 20) return ['Waiting for the AI model…', false];
    return ['Model is busy — retrying…', true];
}

function startOcrProgress() {
    stopOcrProgress();                       // never run two tickers at once
    _ocrStart = Date.now();

    ocrProgress.style.width = '0%';
    ocrProgress.classList.add('is-working');

    _ocrTimer = setInterval(() => {
        const seconds = (Date.now() - _ocrStart) / 1000;
        const pct = OCR_CEILING * (1 - Math.exp(-seconds / OCR_TAU));

        ocrProgress.style.width = pct.toFixed(1) + '%';
        if (ocrProgressPct) ocrProgressPct.textContent = Math.floor(pct) + '%';
        if (ocrProgressElapsed) ocrProgressElapsed.textContent = Math.floor(seconds) + 's';

        const [note, slow] = _ocrPhase(seconds);
        if (ocrProgressNote && ocrProgressNote.textContent !== note) {
            ocrProgressNote.textContent = note;
        }
        if (ocrProgressMeta) ocrProgressMeta.classList.toggle('is-slow', slow);
    }, 150);
}

// complete=true fills to 100% before the next stage; on failure the bar simply
// stops where it is, rather than implying the work finished.
function stopOcrProgress(complete) {
    if (_ocrTimer) {
        clearInterval(_ocrTimer);
        _ocrTimer = null;
    }
    ocrProgress.classList.remove('is-working');

    if (complete) {
        ocrProgress.style.width = '100%';
        if (ocrProgressPct) ocrProgressPct.textContent = '100%';
        if (ocrProgressNote) ocrProgressNote.textContent = 'Extraction complete';
        if (ocrProgressMeta) ocrProgressMeta.classList.remove('is-slow');
    }
}


// Renders the verification verdict: the composite fraud score, the
// spending-anomaly flag, and the reason the risk level landed where it did.
// The score shown is the blend fraud.py returns, NOT the tamper CNN's own
// probability — that arrives separately as tamperProbability. The backend always
// sends these fields (it falls back to a 0.05 baseline when the ML service is
// unreachable), so the block is driven by the response rather than guessed at.
function renderVerification(receiptData) {
    const score = Number(receiptData.fraudScore);
    const level = receiptData.riskLevel || 'Low';
    const hasScore = Number.isFinite(score);

    valRisk.innerText = `${level} risk`;
    valRisk.className = `risk-badge risk-${level.toLowerCase()}`;

    if (!hasScore) {
        verificationDetail.hidden = true;
        return;
    }
    verificationDetail.hidden = false;

    valFraudScore.innerText = score.toFixed(2);
    valFraudScore.classList.toggle('is-flagged', score > 0.7);

    const anomalous = receiptData.anomalyFlag === true;
    valAnomaly.innerText = anomalous ? 'Flagged' : 'Normal';
    valAnomaly.classList.toggle('is-flagged', anomalous);

    // List EVERY signal that fired, not just the first match.
    //
    // The score is a composite — fraud.py starts from the OCR rule signals and
    // adds 0.40 for a perceptual-hash duplicate and 0.40 when the tamper CNN
    // clears 0.50. Showing one cause hid the others: a genuine bill scoring
    // 0.45 displayed only "the amount is unusual" while the tamper signal had
    // also fired, so the number and the explanation did not add up.
    const signals = receiptData.fraudSignals || {};
    const reasons = [];

    if (receiptData.crossUserDuplicate) {
        reasons.push('already submitted by a different account');
    } else if (signals.duplicate) {
        // The perceptual-hash check compares against recent receipts from every
        // account, not just this user's, so it cannot promise whose it was.
        reasons.push('closely matches a receipt already in the system');
    }
    if (signals.tamper) reasons.push('the image shows signs of editing');
    if (receiptData.itemsTotalMismatch) reasons.push('line items do not add up to the total');
    if (anomalous) reasons.push('the amount is unusual for this spend category');
    if (signals.handwritten) reasons.push('handwriting detected on a printed bill');
    if (signals.multi_bill) reasons.push('more than one receipt in the image');
    if (signals.blur) reasons.push('the image is blurred');

    let note = '';
    if (reasons.length === 1) {
        note = reasons[0].charAt(0).toUpperCase() + reasons[0].slice(1) + '.';
    } else if (reasons.length > 1) {
        note = 'Flagged because ' + reasons.slice(0, -1).join(', ')
             + ' and ' + reasons[reasons.length - 1] + '.';
    }
    verifyNote.innerText = note;
    verifyNote.hidden = !note;
}

function processReceiptData(receiptData) {
    activateStep(stepProcess);

    // Populate raw data
    valRawMerchant.innerText = receiptData.rawMerchant || 'Unknown Merchant';
    valDate.innerText = receiptData.date || 'Unknown Date';
    valTotal.innerText = formatCurrency(receiptData.total || 0);

    // Populate items
    if (receiptData.items && Array.isArray(receiptData.items)) {
        valItems.innerHTML = receiptData.items.map(item => `
            <div class="item-row">
                <span>${item.name || 'Item'}</span>
                <span>${item.price != null ? '₹' + parseFloat(item.price).toFixed(2) : '-'}</span>
            </div>
        `).join('');
    } else {
        valItems.innerHTML = `<div class="item-row"><span>No items found</span></div>`;
    }

    // Display Category (from GenAI)
    valCategory.innerText = receiptData.category || 'General';

    // Verification verdict from the fraud and anomaly models
    renderVerification(receiptData);

    // No tamper popup here, deliberately.
    //
    // There was one, and it fired on ordinary receipts. The signal behind it is
    // the CNN clearing 0.50, and at that threshold fraud_cnn.md measures 27.7%
    // false positives on genuine bills out-of-fold — nearer 48% lower down the
    // curve. A modal interrupting one honest user in three to say their photo
    // looks edited is not a fraud control, it is noise, and it trains people to
    // dismiss the warning that matters.
    //
    // The signal is not lost: renderVerification() already lists "the image
    // shows signs of editing" among the reasons, next to the score that earned
    // it. That is the right register for a review signal the model card
    // explicitly says is not a verdict — visible to anyone reading the result,
    // without accusing them mid-flow.
    //
    // If this comes back, it needs a much higher bar than the scoring threshold
    // (0.82 buys 9.2% false positives for 50% recall) — not the same 0.50.
    latestProcessedBillData = {
        merchant: receiptData.rawMerchant || 'Unknown Merchant',
        date: receiptData.date || '-',
        category: receiptData.category || 'General',
        total: Number(receiptData.total || 0),
        items: Array.isArray(receiptData.items) ? receiptData.items : [],
        reference: receiptData.receiptId || `LIVE-${Date.now()}`
    };

    // Move to Reward step
    setTimeout(() => {
        activateStep(stepReward);

        // Display Rewards (calculated on backend)
        valEarnedPoints.innerText = receiptData.rewardPoints || 0;
        valRewardLogic.innerText = receiptData.rewardLogic || '';

        // Store temporarily in the add button for the dashboard UI update
        // We know the DB is already updated! But we wait for user click to show it nicely.
        btnAddBalance.dataset.pendingPoints = receiptData.rewardPoints || 0;
        btnViewDigitalBill.disabled = false;

        showStage(stageResults);

        // Keep history current when user leaves Scan History open during uploads.
        if (getComputedStyle(sectionHistory).display !== 'none') {
            loadScanHistory();
        }

        // Re-rank the vault against the receipt just scanned. The backend has
        // already updated this user's interest vector, so without this the
        // vault keeps showing the ranking from login and a fresh scan appears
        // to change nothing.
        loadRecommendations();
    }, 600);
}

function resetUI() {
    // Reset UI state
    fileInput.value = "";
    stopOcrProgress();
    ocrProgress.style.width = '0%';
    if (ocrProgressPct) ocrProgressPct.textContent = '0%';
    if (ocrProgressElapsed) ocrProgressElapsed.textContent = '0s';
    if (ocrProgressNote) ocrProgressNote.textContent = 'Preparing image…';
    if (ocrProgressMeta) ocrProgressMeta.classList.remove('is-slow');
    clearVerification();
    btnAddBalance.disabled = false;
    btnAddBalance.innerText = "Add to Balance";
    btnViewDigitalBill.disabled = true;
    latestProcessedBillData = null;

    activateStep(stepUpload);
    showStage(stageUpload);
}

// ── SCAN HISTORY ───────────────────────────────────────────────
// Fetches /api/history, renders table rows, and wires the search/filter inputs
async function loadScanHistory() {
    historyLoading.style.display = 'block';
    historyTable.style.display = 'none';
    historyEmpty.style.display = 'none';
    historyEmpty.innerText = 'No scan history found yet.';

    try {
        let data = { history: [] };
        let res = null;

        if (currentUserName === 'Guest Explorer') {
            await new Promise(r => setTimeout(r, 600)); // Simulate delay
            data = {
                history: [
                    { id: 'mock-1', created_at: new Date(Date.now() - 86400000).toISOString(), merchant: 'Big Bazaar', category: 'Supermarket / Grocery', total: 1250, points_earned: 50 },
                    { id: 'mock-2', created_at: new Date(Date.now() - 172800000).toISOString(), merchant: 'Starbucks', category: 'Food & Beverage', total: 450, points_earned: 20 },
                    { id: 'mock-3', created_at: new Date(Date.now() - 259200000).toISOString(), merchant: 'Reliance Digital', category: 'General Retail', total: 10500, points_earned: 420 },
                ]
            };
        } else {
            res = await fetch('/api/history', { headers: getAuthHeaders() });
            if (res.status === 401 || res.status === 403) {
                localStorage.removeItem('token');
                checkAuth();
                return;
            }
            data = await res.json();
        }

        historyLoading.style.display = 'none';

        if (data && data.history && data.history.length > 0) {
            historyTable.style.display = 'table';
            historyTableBody.innerHTML = data.history.map(receipt => `
                <tr class="history-item-row" style="border-bottom: 1px solid #e2e8f0; font-size: 0.9rem;">
                    <td class="history-date" style="padding: 1rem 0.5rem;">${new Date(receipt.created_at).toLocaleDateString()}</td>
                    <td class="history-merchant" style="padding: 1rem 0.5rem; font-weight: 500;">${receipt.merchant || 'Unknown'}</td>
                    <td class="history-category" style="padding: 1rem 0.5rem;"><span class="tag" style="font-size: 0.8rem; padding: 0.2rem 0.6rem;">${receipt.category || 'General'}</span></td>
                    <td style="padding: 1rem 0.5rem;">${formatCurrency(receipt.total || 0)}</td>
                    <td style="padding: 1rem 0.5rem; text-align: right; font-weight: bold; color: var(--color-gold);">+${receipt.points_earned || 0}</td>
                    <td style="padding: 1rem 0.5rem; text-align: center;">
                        <button class="btn btn-secondary btn-sm history-view-bill"
                            data-receipt-id="${receipt.id}"
                            data-merchant="${receipt.merchant || 'Unknown Merchant'}"
                            data-date="${receipt.date || ''}"
                            data-category="${receipt.category || 'General'}"
                            data-total="${Number(receipt.total || 0)}">
                            View Digital Bill
                        </button>
                    </td>
                </tr>
            `).join('');
            filterHistoryTable();
        } else {
            historyTableBody.innerHTML = '';
            historyEmpty.style.display = 'block';
        }
    } catch (error) {
        console.error("Error fetching history:", error);
        historyLoading.style.display = 'none';
        historyTableBody.innerHTML = '';
        historyEmpty.style.display = 'block';
        historyEmpty.innerText = 'Failed to load history.';
    }
}

// --- Interactions ---

btnAddBalance.addEventListener('click', async () => {
    const pointsToAdd = parseInt(btnAddBalance.dataset.pendingPoints || 0);
    if (pointsToAdd > 0) {
        btnAddBalance.disabled = true;
        btnAddBalance.innerText = "Syncing...";

        try {
            await fetchTotalPoints();
            totalPointsDisplay.classList.add('bump');
            setTimeout(() => totalPointsDisplay.classList.remove('bump'), 300);
        } catch (error) {
            console.error('Failed to sync points:', error);
        }

        btnAddBalance.dataset.pendingPoints = 0;
        btnAddBalance.innerText = "Synced!";
    }
});

btnReset.addEventListener('click', resetUI);

btnViewHistory.addEventListener('click', async () => {
    sectionHistory.style.display = 'block';
    btnViewHistory.style.display = 'none';
    await loadScanHistory();
});

btnCloseHistory.addEventListener('click', () => {
    sectionHistory.style.display = 'none';
    btnViewHistory.style.display = 'inline-block';
});

historyTableBody.addEventListener('click', async (e) => {
    const viewBillBtn = e.target.closest('.history-view-bill');
    if (!viewBillBtn) return;

    const receiptId = viewBillBtn.dataset.receiptId;
    viewBillBtn.disabled = true;
    const originalText = viewBillBtn.innerText;
    viewBillBtn.innerText = 'Loading...';

    const fallbackBill = {
        merchant: viewBillBtn.dataset.merchant,
        date: viewBillBtn.dataset.date,
        category: viewBillBtn.dataset.category,
        total: Number(viewBillBtn.dataset.total || 0),
        items: [],
        reference: receiptId
    };

    if (currentUserName === 'Guest Explorer') {
        openDigitalBillModal(fallbackBill);
        viewBillBtn.disabled = false;
        viewBillBtn.innerText = originalText;
        return;
    }

    try {
        const response = await fetch(`/api/receipt/${encodeURIComponent(receiptId)}`, { headers: getAuthHeaders() });
        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem('token');
            checkAuth();
            return;
        }

        if (!response.ok) {
            openDigitalBillModal(fallbackBill);
            return;
        }

        const data = await response.json();
        const receipt = data?.receipt || {};
        openDigitalBillModal({
            merchant: receipt.merchant || viewBillBtn.dataset.merchant,
            date: receipt.date || viewBillBtn.dataset.date,
            category: receipt.category || viewBillBtn.dataset.category,
            total: Number(receipt.total || viewBillBtn.dataset.total || 0),
            items: Array.isArray(data.items) ? data.items : [],
            reference: receiptId
        });
    } catch (error) {
        console.error('Failed to fetch digital bill details:', error);
    } finally {
        viewBillBtn.disabled = false;
        viewBillBtn.innerText = originalText;
    }
});

async function loadClaimedHistory() {
    // Do NOT blank the table here. On open it holds skeleton rows, and on a
    // refresh-in-place it holds the previous claims — clearing either would
    // flash an empty table for the length of the request. The rows are replaced
    // wholesale once the data arrives, and the empty/error branches below clear
    // the placeholders themselves.
    const hasSkeletons = !!claimedTableBody.querySelector('.claimed-skeleton-row');
    claimedLoading.style.display = hasSkeletons ? 'none' : 'block';
    claimedEmpty.style.display = 'none';

    try {
        let claimsData = [];
        if (currentUserName === 'Guest Explorer') {
            await new Promise(r => setTimeout(r, 400)); // Simulate delay
            // Give the guest one mock claimed item if we want
            claimsData = [
                { created_at: new Date(Date.now() - 3600000).toISOString(), type: 'voucher', title: 'Domino\'s Voucher', claim_code: '41920381923', required_points: 150 }
            ]
        } else {
            const response = await fetch('/api/claimed-rewards', { headers: getAuthHeaders() });
            if (response.status === 401 || response.status === 403) {
                clearClaimedSkeletons();   // else the placeholders outlive the session
                localStorage.removeItem('token');
                checkAuth();
                return;
            }

            const data = await response.json();
            claimsData = data.claims || [];
        }

        claimedLoading.style.display = 'none';

        if (Array.isArray(claimsData) && claimsData.length > 0) {
            claimedTableBody.innerHTML = claimsData.map(claim => `
                <tr class="history-item-row" style="border-bottom: 1px solid #e2e8f0; font-size: 0.9rem;">
                    <td style="padding: 1rem 0.5rem;">${new Date(claim.created_at).toLocaleDateString()}</td>
                    <td style="padding: 1rem 0.5rem;"><span class="tag" style="font-size: 0.75rem;">${claim.type || 'voucher'}</span></td>
                    <td style="padding: 1rem 0.5rem; font-weight: 500;">${claim.title || 'Reward'}</td>
                    <td style="padding: 1rem 0.5rem;">
                        <div class="claimed-code-cell">
                            <span class="claimed-code-value">${claim.claim_code || '--'}</span>
                            <button type="button"
                                class="claimed-copy-btn"
                                data-copy-code="${claim.claim_code || ''}"
                                aria-label="Copy claimed voucher code"
                                ${claim.claim_code ? '' : 'disabled'}>
                                📋
                            </button>
                        </div>
                    </td>
                    <td style="padding: 1rem 0.5rem; text-align: right; font-weight: bold; color: #b91c1c;">-${claim.required_points || 0}</td>
                </tr>
            `).join('');
        } else {
            clearClaimedSkeletons();
            claimedEmpty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error fetching claimed history:', error);
        clearClaimedSkeletons();
        claimedLoading.style.display = 'none';
        claimedEmpty.style.display = 'block';
        claimedEmpty.innerText = 'Failed to load claimed vouchers.';
    }
}

claimedTableBody.addEventListener('click', async (e) => {
    const copyBtn = e.target.closest('.claimed-copy-btn');
    if (!copyBtn || copyBtn.disabled) return;

    const code = String(copyBtn.dataset.copyCode || '').trim();
    if (!code) return;

    const copied = await copyTextToClipboard(code);
    const previousLabel = copyBtn.innerText;
    copyBtn.innerText = copied ? '✓' : '✕';
    copyBtn.disabled = true;

    window.setTimeout(() => {
        copyBtn.innerText = previousLabel || '📋';
        copyBtn.disabled = false;
    }, 1100);
});

claimCardsGrid.addEventListener('click', async (e) => {
    const scratchBtn = e.target.closest('[data-scratch-btn]');
    if (scratchBtn) {
        const card = scratchBtn.closest('.claim-card');
        if (!card || card.dataset.claimed === 'true') return;
        await claimRewardFromCard(card, scratchBtn);
        return;
    }

    const voucherBtn = e.target.closest('[data-voucher-btn]');
    if (voucherBtn) {
        const card = voucherBtn.closest('.claim-card');
        if (!card || card.dataset.claimed === 'true') return;
        await claimRewardFromCard(card, voucherBtn);
    }
});

// ── HISTORY SEARCH & FILTER ─────────────────────────────────────
// Client-side text search + category dropdown applied to the rendered table rows
const historySearchInput = document.getElementById('history-search');
const historyCategoryFilter = document.getElementById('history-category-filter');

function filterHistoryTable() {
    if (!historySearchInput || !historyCategoryFilter) return;

    const searchTerm = historySearchInput.value.toLowerCase().trim();
    const filterCategory = historyCategoryFilter.value.toLowerCase();
    const rows = historyTableBody.querySelectorAll('.history-item-row');
    let visibleCount = 0;

    rows.forEach(row => {
        const date = row.querySelector('.history-date').innerText.toLowerCase();
        const merchant = row.querySelector('.history-merchant').innerText.toLowerCase();
        const category = row.querySelector('.history-category').innerText.toLowerCase();

        // Check text search match
        const matchesSearch = date.includes(searchTerm) || merchant.includes(searchTerm) || category.includes(searchTerm);

        // Check dropdown select match
        const matchesCategory = filterCategory === 'all' || category.includes(filterCategory);

        if (matchesSearch && matchesCategory) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Show empty state if no results match the search/filter
    if (visibleCount === 0 && rows.length > 0) {
        historyEmpty.innerText = 'No matching bills found.';
        historyEmpty.style.display = 'block';
        historyTable.style.display = 'none';
    } else if (visibleCount > 0) {
        historyEmpty.style.display = 'none';
        historyTable.style.display = 'table';
    }
}

if (historySearchInput) {
    historySearchInput.addEventListener('input', filterHistoryTable);
}
if (historyCategoryFilter) {
    historyCategoryFilter.addEventListener('change', filterHistoryTable);
}

/* ── CUSTOM SELECT ──────────────────────────────────────────────
   Enhances a real <select> rather than replacing it. The native element stays
   in the DOM as the source of truth, so `historyCategoryFilter.value` and the
   'change' listener in filterHistoryTable() keep working untouched — and if
   this never runs, the page still has a usable control. */
function enhanceSelect(selectEl) {
    if (!selectEl || selectEl.dataset.enhanced === 'true') return;
    selectEl.dataset.enhanced = 'true';

    const wrap = document.createElement('div');
    wrap.className = 'custom-select';
    selectEl.parentNode.insertBefore(wrap, selectEl);
    wrap.appendChild(selectEl);
    selectEl.classList.add('custom-select__native');

    const trigger = document.createElement('button');
    trigger.type = 'button';                  // never submit a surrounding form
    trigger.className = 'custom-select__trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.innerHTML = '<span class="custom-select__label"></span>'
                      + '<span class="custom-select__caret" aria-hidden="true">▾</span>';

    const panel = document.createElement('ul');
    panel.className = 'custom-select__panel';
    panel.setAttribute('role', 'listbox');

    const label = trigger.querySelector('.custom-select__label');
    const options = Array.from(selectEl.options);

    options.forEach((opt, i) => {
        const li = document.createElement('li');
        li.className = 'custom-select__option';
        li.setAttribute('role', 'option');
        li.dataset.index = String(i);
        li.textContent = opt.textContent;
        panel.appendChild(li);
    });

    wrap.appendChild(trigger);
    wrap.appendChild(panel);

    const items = Array.from(panel.children);
    let activeIndex = selectEl.selectedIndex;

    function syncFromNative() {
        const i = selectEl.selectedIndex;
        label.textContent = options[i] ? options[i].textContent : '';
        items.forEach((li, n) => li.setAttribute('aria-selected', n === i ? 'true' : 'false'));
    }

    function setActive(i) {
        activeIndex = Math.max(0, Math.min(items.length - 1, i));
        items.forEach((li, n) => li.classList.toggle('is-active', n === activeIndex));
        items[activeIndex].scrollIntoView({ block: 'nearest' });
    }

    function open() {
        wrap.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
        setActive(selectEl.selectedIndex);
    }

    function close() {
        wrap.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
        items.forEach(li => li.classList.remove('is-active'));
    }

    function choose(i) {
        if (selectEl.selectedIndex !== i) {
            selectEl.selectedIndex = i;
            // Dispatch so existing listeners fire — assigning .value in code
            // does not raise 'change' on its own.
            selectEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
        syncFromNative();
        close();
        trigger.focus();
    }

    trigger.addEventListener('click', () => {
        wrap.classList.contains('is-open') ? close() : open();
    });

    panel.addEventListener('click', e => {
        const li = e.target.closest('.custom-select__option');
        if (li) choose(Number(li.dataset.index));
    });

    trigger.addEventListener('keydown', e => {
        const isOpen = wrap.classList.contains('is-open');
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            if (!isOpen) return open();
            setActive(activeIndex + (e.key === 'ArrowDown' ? 1 : -1));
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            isOpen ? choose(activeIndex) : open();
        } else if (e.key === 'Escape' && isOpen) {
            close();
        } else if (e.key === 'Home' && isOpen) {
            e.preventDefault(); setActive(0);
        } else if (e.key === 'End' && isOpen) {
            e.preventDefault(); setActive(items.length - 1);
        }
    });

    document.addEventListener('click', e => {
        if (!wrap.contains(e.target)) close();
    });

    // Keep the label honest if anything sets the value programmatically.
    selectEl.addEventListener('change', syncFromNative);
    syncFromNative();
}

document.querySelectorAll('select.history-select').forEach(enhanceSelect);
