// --- State Management ---
let totalPoints = 0;

// --- DOM Elements ---
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

// Result Elements
const valRawMerchant = document.getElementById('val-raw-merchant');
const valDate = document.getElementById('val-date');
const valTotal = document.getElementById('val-total');
const valItems = document.getElementById('val-items');
const valCategory = document.getElementById('val-category');
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

// API Auth Headers helper
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

function generateClaimCatalog() {
    const vouchers = [];
    const shuffledVouchers = shuffleArray(VOUCHER_POOL);
    for (let i = 0; i < 9; i += 1) {
        const voucher = shuffledVouchers[i % shuffledVouchers.length];
        vouchers.push({
            type: 'voucher',
            icon: voucher.icon,
            title: voucher.title,
            offer: voucher.offer,
            requiredPoints: randomIntBetween(20, 90)
        });
    }

    const scratches = [];
    for (let i = 0; i < 3; i += 1) {
        scratches.push({
            type: 'scratch',
            icon: '🃏',
            title: `Scratch & Win Card ${i + 1}`,
            offer: 'Scratch the card to reveal your reward',
            reward: randomPick(SCRATCH_REWARD_POOL),
            requiredPoints: randomIntBetween(20, 90)
        });
    }

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

async function openClaimModal() {
    if (!localStorage.getItem('token') && currentUserName !== 'Guest Explorer') {
        openAuthModal(true);
        return;
    }
    if (localStorage.getItem('token')) {
        await fetchTotalPoints();
    }
    renderClaimCards();
    refreshClaimButtonStates();
    claimAvailablePoints.innerText = totalPoints;
    claimModal.classList.remove('hidden');
    syncBodyScrollLock();

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
    await loadClaimedHistory();
    claimedModal.classList.remove('hidden');
    syncBodyScrollLock();
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

        // Numbers
        analyticsTotalBills.innerText = s.totalBills;
        analyticsTotalSpend.innerText = `₹${s.totalSpend.toLocaleString('en-IN')}`;
        analyticsAvgBillValue.innerText = `₹${s.avgBillValue.toLocaleString('en-IN')}`;
        analyticsTotalPoints.innerText = s.totalPointsEarned;
        analyticsTopCategoryLabel.innerText = s.topCategory;
        analyticsTopMerchantLabel.innerText = s.topMerchant;
        analyticsMainInterest.innerText = s.topCategory;

        // Donut Chart simulation
        if (data.categories && data.categories.length > 0) {
            const palette = ['#5ba3e8', '#2d6bb5', '#ffd93d', '#ff6b6b', '#6bc167'];
            let currentPct = 0;
            const gradientParts = data.categories.map((c, i) => {
                const color = palette[i % palette.length];
                const start = currentPct;
                currentPct += c.percentage;
                return `${color} ${start}% ${currentPct}%`;
            });
            analyticsCategoryChart.style.background = `conic-gradient(${gradientParts.join(', ')})`;

            // Legend
            analyticsLegend.innerHTML = data.categories.map((c, i) => `
                <li>
                    <span class="legend-color" style="background: ${palette[i % palette.length]}"></span>
                    <span class="legend-label">${c.name}</span>
                    <span class="legend-value">${c.percentage}%</span>
                </li>
            `).join('');
        }

        // Insights
        if (data.insights && data.insights.length > 0) {
            analyticsInsightsList.innerHTML = data.insights.map(ins => `
                <li class="insight-item">
                    <div class="insight-icon">💡</div>
                    <div class="insight-body">
                        <h4>${ins.title}</h4>
                        <p>${ins.text}</p>
                    </div>
                </li>
            `).join('');
        } else {
            analyticsInsightsList.innerHTML = '<li>No insights available yet.</li>';
        }

    } catch (err) {
        console.error(err);
        analyticsLoading.innerText = "Error loading analytics. Please try again.";
    }
}

// --- Error Modal Logic ---

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

    const originalText = buttonEl.innerText;
    buttonEl.disabled = true;
    buttonEl.innerText = 'Claiming...';

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
                localStorage.removeItem('token');
                checkAuth();
                return;
            }

            data = await response.json();
            if (!response.ok || !data.success) {
                buttonEl.disabled = false;
                buttonEl.innerText = originalText;
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
        buttonEl.disabled = false;
        buttonEl.innerText = originalText;
        alert('Network error while claiming reward.');
    }
}

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

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    startHeroTyping();
});

function startHeroTyping() {
    if (!heroTypingTitle) return;

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

// --- Auth Logic ---

function setAuthMode(loginMode) {
    isLoginMode = loginMode;
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

        // Give guest some points to explore the reward UI
        totalPoints = 500;
        totalPointsDisplay.innerText = totalPoints;
        claimAvailablePoints.innerText = totalPoints;

        await playWelcomeIntro('Guest Explorer');
        appContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    valEarnedPoints.innerText = '0';
    valRewardLogic.innerText = '--';
    resetUI();
    closeAuthModal();
    closeClaimModal();
    closeClaimSuccessModal();
    closeDigitalBillModal();
    checkAuth();
});

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

// --- Utility Functions ---

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

// --- Core Logic ---

// 1. Upload Handler
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

    // Start an infinite progress bar for the UI while waiting for the Gemini API
    ocrProgress.style.transition = 'width 10s ease-out';
    ocrProgress.style.width = '90%';

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
                ocrProgress.style.transition = 'width 0.2s linear';
                ocrProgress.style.width = '100%';

                setTimeout(() => {
                    processReceiptData(result.data);
                }, 500);
            } else if (status === 409) {
                openErrorModal('Duplicate Receipt Detected', result.error || 'This receipt has already been processed.', '⚠️');
                resetUI();
            } else if (status === 422) {
                openErrorModal('Scan Failed', result.error || 'The receipt image is blurry or unreadable. Please try again with a clearer photo.', '📷');
                resetUI();
            } else if (status === 429) {
                openErrorModal('Rate Limit Exceeded', result.error || 'The AI service is currently busy. Please try again in a few moments.', '⏳');
                resetUI();
            } else {
                openErrorModal('Processing Error', 'Error processing receipt: ' + (result.error || `HTTP Status ${status}`), '📡');
                resetUI();
            }
        } catch (error) {
            console.error('Upload Error:', error);
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

// 2. Process Data
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
    }, 600);
}

function resetUI() {
    // Reset UI state
    fileInput.value = "";
    ocrProgress.style.width = '0%';
    btnAddBalance.disabled = false;
    btnAddBalance.innerText = "Add to Balance";
    btnViewDigitalBill.disabled = true;
    latestProcessedBillData = null;

    activateStep(stepUpload);
    showStage(stageUpload);
}

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
    claimedLoading.style.display = 'block';
    claimedEmpty.style.display = 'none';
    claimedTableBody.innerHTML = '';

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
            claimedEmpty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error fetching claimed history:', error);
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

// History Search & Filter Logic
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
