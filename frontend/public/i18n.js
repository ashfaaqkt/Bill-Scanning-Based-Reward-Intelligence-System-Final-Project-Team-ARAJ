// ── Landing-page internationalisation (English, Arabic, Hindi, Malayalam, Chinese) ──
// Text-only nodes use [data-i18n]; nodes with inline markup use [data-i18n-html].
// Arabic switches the landing section to RTL; the others stay LTR like English.
// Technical identifiers (endpoints, tech stacks, product names) intentionally stay in English.
(function () {
    'use strict';

    var ARAJ = '<span class="araj"><span class="araj-a">A</span><span class="araj-r">R</span>' +
        '<span class="araj-a2">A</span><span class="araj-j">J</span></span>';

    var T = {
        en: {
            badge: 'CAPSTONE PROJECT • BITS PILANI DIGITAL',
            heroTitle: 'Turn Every Receipt Into Rewards',
            heroSubtitle: 'An intelligent capstone project powered by Gemini AI. Scan bills, earn points, and experience the future of retail rewards.',
            btnSignIn: 'Sign In / Sign Up',
            btnGuest: 'Explore as Guest',
            feat1t: 'Instant OCR', feat1d: 'AI extracts line-item data in seconds',
            feat2t: 'Fraud Detection', feat2d: 'Duplicate, tamper and anomaly checks on every scan',
            feat3t: 'Smart Multipliers', feat3d: 'Category & streak-based rewards',
            feat4t: 'Privacy First', feat4d: 'Enterprise-grade data handling',
            learnMore: 'Learn More',
            whatT: 'What is this system?',
            whatD: 'The Bill Scanning Reward AI System is a final-year capstone project leveraging cutting-edge Gemini AI to digitize, analyze, and process retail receipts. It instantly extracts line-item data, dynamically validates duplicate scans, and calculates intelligent reward multipliers based on shopping categories and user streak behavior. It transforms routine shopping into an engaging, gamified experience while ensuring privacy and enterprise-level data handling.',
            teamT: 'Who is Team ' + ARAJ + '?',
            teamD: 'Team ' + ARAJ + ' (Group 120) consists of four passionate B.Sc. Computer Science students from BITS Pilani Digital. We engineered this secure, dynamic, and state-of-the-art rewards infrastructure.',
            role1: 'Team Lead & Lead Developer',
            role2: 'Fraud Detection & QA',
            role3: 'ML Research & Dataset',
            role4: 'Data Labelling & Documentation',
            aboutTitle: 'About This Capstone Project',
            aboutIntro: 'This is the final-year <strong>Capstone Project</strong> of Team ARAJ (Group 120), B.Sc. Computer Science at <strong>BITS Pilani Digital</strong>, under the guidance of <strong>Prof. Uma Sankara Rao</strong>. It demonstrates an end-to-end receipt-scanning reward pipeline — OCR, fraud detection, spend classification, and personalised rewards — as an <strong>academic study</strong>, not a commercial product.',
            scopeTitle: 'Scope & current status:',
            scope1: 'OCR is live (Google Gemini 2.5 Flash).',
            scope2: 'All five ML models trained, integrated and verified end to end — category, fraud, tamper, anomaly and recommender.',
            scope3: 'Reward, claim & analytics logic functional on a live backend + Firestore.',
            scope4: 'Built for demonstration and study — not production-hardened.',
            btnCapstoneRepo: '📦 Capstone Repository',
            btnPocRepo: '🔬 Phase 3 PoC · Study Project',
            hiwTitle: 'How It Works',
            hiwLead: "From a photo of a receipt to reward points in seconds — here's the full journey, and the architecture that powers it.",
            s1t: '📤 Upload', s1d: 'You drop a receipt image in the browser. The single-page frontend sends it to the backend over an authenticated (JWT) request.',
            s2t: '🔍 Extract — OCR', s2d: 'The backend forwards the image to the ML microservice, where a 5-layer OCR pipeline runs: a sharpness check that refuses unreadable photos before any AI spend, a rate-limit gate, Google Gemini 2.5 Flash extraction, a model fallback, and a pixel-density scan that flags handwritten edits.',
            s3t: '🧠 Classify & Detect', s3d: 'The extracted fields flow through the ML models — a TF-IDF + Random Forest category classifier, a fraud scorer combining OCR signals, perceptual-hash duplicate matching and a MobileNetV2 tamper network, and an Isolation-Forest spending-anomaly check.',
            s4t: '🎁 Reward & Recommend', s4d: 'A receipt already claimed — by you or by anyone else — is refused here and earns nothing. Otherwise the points engine computes ₹100 = 1 point, scaled by spend category, user tier and streak, and the points, fraud verdict and personalised offers are written to Firestore and returned to your screen.',
            archTitle: 'Under the Hood — Architecture',
            archLead: 'A three-tier design keeps the AI/ML layer isolated from the app logic, so each part can evolve independently.',
            c1t: 'Frontend', c1d: 'Single-page app with a 4-step stepper. Handles upload, auth UI and live result rendering.',
            c2t: 'Backend API', c2d: 'Orchestrates the pipeline: JWT auth, reward & claim logic, and talks to the database.',
            c3t: 'ML Microservice', c3d: 'Isolated Python service hosting OCR + every ML model behind <code>/ml/*</code> endpoints.',
            c4t: 'Data & AI', c4d: 'Firestore stores users, receipts, points & fraud scores; Gemini powers the OCR extraction.',
            requestFlow: 'Request flow',
            trust1: '🏛️ <strong>BITS Pilani</strong> Digital',
            trust2: '🤖 Powered by <strong>Google Gemini AI</strong>',
            trust3: '👥 Group 120 — <strong>Team ' + ARAJ + '</strong>'
        },

        ar: {
            badge: 'مشروع تخرّج • BITS PILANI DIGITAL',
            heroTitle: 'حوِّل كل فاتورة إلى مكافآت',
            heroSubtitle: 'مشروع تخرّج ذكي مدعوم بالذكاء الاصطناعي Gemini. امسح الفواتير، واكسب النقاط، واختبر مستقبل مكافآت التجزئة.',
            btnSignIn: 'تسجيل الدخول / إنشاء حساب',
            btnGuest: 'الدخول كضيف',
            feat1t: 'مسح فوري (OCR)', feat1d: 'يستخرج الذكاء الاصطناعي بيانات البنود خلال ثوانٍ',
            feat2t: 'كشف الاحتيال', feat2d: 'فحص التكرار والتلاعب والشذوذ في كل عملية مسح',
            feat3t: 'مضاعفات ذكية', feat3d: 'مكافآت حسب الفئة وسلسلة الاستخدام',
            feat4t: 'الخصوصية أولاً', feat4d: 'معالجة بيانات بمستوى المؤسسات',
            learnMore: 'اعرف المزيد',
            whatT: 'ما هذا النظام؟',
            whatD: 'نظام مكافآت مسح الفواتير هو مشروع تخرّج نهائي يستخدم أحدث تقنيات الذكاء الاصطناعي Gemini لرقمنة إيصالات التجزئة وتحليلها ومعالجتها. يستخرج بيانات البنود فورًا، ويتحقق ديناميكيًا من عمليات المسح المكرّرة، ويحسب مضاعفات مكافآت ذكية بناءً على فئات التسوق وسلوك المستخدم. يحوّل التسوق الاعتيادي إلى تجربة تفاعلية ممتعة مع ضمان الخصوصية ومعالجة البيانات بمستوى المؤسسات.',
            teamT: 'من هو فريق ' + ARAJ + '؟',
            teamD: 'يتألف فريق ' + ARAJ + ' (المجموعة 120) من أربعة طلاب شغوفين في بكالوريوس علوم الحاسب من BITS Pilani Digital. صمّمنا هذه البنية الآمنة والديناميكية والمتطورة للمكافآت.',
            role1: 'قائد الفريق والمطوّر الرئيسي',
            role2: 'كشف الاحتيال وضمان الجودة',
            role3: 'أبحاث تعلّم الآلة والبيانات',
            role4: 'توسيم البيانات والتوثيق',
            aboutTitle: 'عن مشروع التخرّج هذا',
            aboutIntro: 'هذا هو <strong>مشروع التخرّج</strong> النهائي لفريق ARAJ (المجموعة 120)، بكالوريوس علوم الحاسب في <strong>BITS Pilani Digital</strong>، بإشراف <strong>البروفيسور أوما سانكارا راو</strong>. يعرض خط معالجة متكامل لمسح الإيصالات ومنح المكافآت — التعرّف الضوئي، كشف الاحتيال، تصنيف الإنفاق، والمكافآت المخصّصة — بوصفه <strong>دراسة أكاديمية</strong> وليس منتجًا تجاريًا.',
            scopeTitle: 'النطاق والحالة الحالية:',
            scope1: 'التعرّف الضوئي (OCR) يعمل مباشرةً (Google Gemini 2.5 Flash).',
            scope2: 'جميع نماذج التعلُّم الآلي الخمسة مُدرَّبة ومُدمَجة ومُتحقَّق منها من طرف إلى طرف: التصنيف والاحتيال والتلاعب والشذوذ والتوصية.',
            scope3: 'منطق المكافآت والمطالبات والتحليلات يعمل على خادم حي + Firestore.',
            scope4: 'مبني للعرض والدراسة — غير مُهيّأ للإنتاج.',
            btnCapstoneRepo: '📦 مستودع المشروع',
            btnPocRepo: '🔬 المرحلة 3 (إثبات المفهوم) · مشروع دراسي',
            hiwTitle: 'كيف يعمل',
            hiwLead: 'من صورة إيصال إلى نقاط مكافآت خلال ثوانٍ — إليك الرحلة الكاملة والبنية التي تشغّلها.',
            s1t: '📤 الرفع', s1d: 'تقوم برفع صورة الإيصال في المتصفّح. ترسلها الواجهة الأمامية إلى الخادم عبر طلب موثّق (JWT).',
            s2t: '🔍 الاستخراج — OCR', s2d: 'يمرّر الخادم الصورة إلى خدمة تعلّم الآلة حيث يعمل خط معالجة OCR من 5 طبقات: فحص حِدّة يرفض الصور غير المقروءة قبل أي استهلاك للذكاء الاصطناعي، وبوابة تحديد المعدّل، واستخراج Google Gemini 2.5 Flash، واحتياطي للنموذج، ومسح كثافة البكسل الذي يُبلّغ عن التعديلات المكتوبة بخط اليد.',
            s3t: '🧠 التصنيف والكشف', s3d: 'تمرّ الحقول المستخرجة عبر نماذج تعلّم الآلة — مُصنِّف فئات TF-IDF + Random Forest، ومُقيِّم احتيال يجمع بين إشارات OCR ومطابقة التكرار بالتجزئة الإدراكية وشبكة MobileNetV2 لكشف التلاعب، وفحص شذوذ الإنفاق بـ Isolation-Forest.',
            s4t: '🎁 المكافأة والتوصية', s4d: 'الإيصال الذي سبقت المطالبة به — منك أو من أي شخص آخر — يُرفض هنا ولا يمنح أي نقاط. وإلا يحسب محرّك النقاط ₹100 = نقطة واحدة، مع تعديلها حسب فئة الإنفاق ومستوى المستخدم والسلسلة، وتُكتب النقاط وحُكم الاحتيال والعروض المخصّصة في Firestore وتُعاد إلى شاشتك.',
            archTitle: 'خلف الكواليس — البنية',
            archLead: 'تصميم من ثلاث طبقات يعزل طبقة الذكاء الاصطناعي/تعلّم الآلة عن منطق التطبيق، بحيث يتطوّر كل جزء بشكل مستقل.',
            c1t: 'الواجهة الأمامية', c1d: 'تطبيق أحادي الصفحة بأربع خطوات. يتولّى الرفع وواجهة الدخول وعرض النتائج الحية.',
            c2t: 'واجهة الخادم', c2d: 'ينسّق خط المعالجة: مصادقة JWT، ومنطق المكافآت والمطالبات، والتواصل مع قاعدة البيانات.',
            c3t: 'خدمة تعلّم الآلة', c3d: 'خدمة Python معزولة تستضيف OCR وكل نماذج تعلّم الآلة خلف نقاط النهاية <code>/ml/*</code>.',
            c4t: 'البيانات والذكاء الاصطناعي', c4d: 'يخزّن Firestore المستخدمين والإيصالات والنقاط ودرجات الاحتيال؛ ويشغّل Gemini استخراج OCR.',
            requestFlow: 'مسار الطلب',
            trust1: '🏛️ <strong>BITS Pilani</strong> Digital',
            trust2: '🤖 مدعوم بـ <strong>Google Gemini AI</strong>',
            trust3: '👥 المجموعة 120 — <strong>فريق ' + ARAJ + '</strong>'
        },

        hi: {
            badge: 'कैपस्टोन प्रोजेक्ट • BITS PILANI DIGITAL',
            heroTitle: 'हर रसीद को इनामों में बदलें',
            heroSubtitle: 'Gemini AI द्वारा संचालित एक बुद्धिमान कैपस्टोन प्रोजेक्ट। बिल स्कैन करें, पॉइंट कमाएँ और रिटेल रिवॉर्ड्स के भविष्य का अनुभव करें।',
            btnSignIn: 'साइन इन / साइन अप',
            btnGuest: 'अतिथि के रूप में देखें',
            feat1t: 'इंस्टेंट OCR', feat1d: 'AI सेकंडों में लाइन-आइटम डेटा निकालता है',
            feat2t: 'धोखाधड़ी पहचान', feat2d: 'हर स्कैन पर डुप्लिकेट, छेड़छाड़ और विसंगति जाँच',
            feat3t: 'स्मार्ट मल्टीप्लायर', feat3d: 'श्रेणी और स्ट्रीक-आधारित इनाम',
            feat4t: 'प्राइवेसी सर्वप्रथम', feat4d: 'एंटरप्राइज़-ग्रेड डेटा हैंडलिंग',
            learnMore: 'और जानें',
            whatT: 'यह सिस्टम क्या है?',
            whatD: 'बिल स्कैनिंग रिवॉर्ड AI सिस्टम एक फाइनल-ईयर कैपस्टोन प्रोजेक्ट है जो रिटेल रसीदों को डिजिटाइज़, विश्लेषण और प्रोसेस करने के लिए अत्याधुनिक Gemini AI का उपयोग करता है। यह तुरंत लाइन-आइटम डेटा निकालता है, डुप्लिकेट स्कैन को गतिशील रूप से सत्यापित करता है, और खरीदारी श्रेणियों तथा उपयोगकर्ता स्ट्रीक व्यवहार के आधार पर बुद्धिमान इनाम मल्टीप्लायर की गणना करता है। यह रोज़मर्रा की खरीदारी को एक आकर्षक, गेमिफाइड अनुभव में बदल देता है, साथ ही प्राइवेसी और एंटरप्राइज़-स्तरीय डेटा हैंडलिंग सुनिश्चित करता है।',
            teamT: 'टीम ' + ARAJ + ' कौन है?',
            teamD: 'टीम ' + ARAJ + ' (ग्रुप 120) में BITS Pilani Digital के चार उत्साही B.Sc. कंप्यूटर साइंस छात्र शामिल हैं। हमने यह सुरक्षित, गतिशील और अत्याधुनिक रिवॉर्ड्स इंफ्रास्ट्रक्चर तैयार किया है।',
            role1: 'टीम लीड और लीड डेवलपर',
            role2: 'धोखाधड़ी पहचान और QA',
            role3: 'ML रिसर्च और डेटासेट',
            role4: 'डेटा लेबलिंग और दस्तावेज़ीकरण',
            aboutTitle: 'इस कैपस्टोन प्रोजेक्ट के बारे में',
            aboutIntro: 'यह टीम ARAJ (ग्रुप 120) का फाइनल-ईयर <strong>कैपस्टोन प्रोजेक्ट</strong> है, B.Sc. कंप्यूटर साइंस, <strong>BITS Pilani Digital</strong>, <strong>प्रो. उमा शंकर राव</strong> के मार्गदर्शन में। यह एक एंड-टू-एंड रसीद-स्कैनिंग रिवॉर्ड पाइपलाइन — OCR, धोखाधड़ी पहचान, खर्च वर्गीकरण और व्यक्तिगत इनाम — को एक <strong>अकादमिक अध्ययन</strong> के रूप में प्रदर्शित करता है, न कि व्यावसायिक उत्पाद के रूप में।',
            scopeTitle: 'दायरा और वर्तमान स्थिति:',
            scope1: 'OCR लाइव है (Google Gemini 2.5 Flash)।',
            scope2: 'पाँचों ML मॉडल प्रशिक्षित, एकीकृत और आरंभ से अंत तक सत्यापित — श्रेणी, धोखाधड़ी, छेड़छाड़, विसंगति और अनुशंसा।',
            scope3: 'रिवॉर्ड, क्लेम और एनालिटिक्स लॉजिक लाइव बैकएंड + Firestore पर कार्यशील।',
            scope4: 'प्रदर्शन और अध्ययन के लिए बनाया गया — प्रोडक्शन-हार्डन्ड नहीं।',
            btnCapstoneRepo: '📦 कैपस्टोन रिपॉज़िटरी',
            btnPocRepo: '🔬 फेज़ 3 PoC · स्टडी प्रोजेक्ट',
            hiwTitle: 'यह कैसे काम करता है',
            hiwLead: 'रसीद की एक तस्वीर से कुछ ही सेकंड में रिवॉर्ड पॉइंट तक — यहाँ पूरी यात्रा और इसे संचालित करने वाली आर्किटेक्चर है।',
            s1t: '📤 अपलोड', s1d: 'आप ब्राउज़र में रसीद की छवि डालते हैं। सिंगल-पेज फ्रंटएंड इसे एक प्रमाणित (JWT) अनुरोध के ज़रिए बैकएंड को भेजता है।',
            s2t: '🔍 एक्सट्रैक्ट — OCR', s2d: 'बैकएंड छवि को ML माइक्रोसर्विस को भेजता है, जहाँ 5-लेयर OCR पाइपलाइन चलती है: एक शार्पनेस जाँच जो किसी भी AI खर्च से पहले अपठनीय तस्वीरें अस्वीकार कर देती है, रेट-लिमिट गेट, Google Gemini 2.5 Flash निष्कर्षण, मॉडल फ़ॉलबैक, और हस्तलिखित बदलावों को चिह्नित करने वाला पिक्सेल-घनत्व स्कैन।',
            s3t: '🧠 वर्गीकरण और पहचान', s3d: 'निकाले गए फ़ील्ड ML मॉडलों से गुज़रते हैं — TF-IDF + Random Forest श्रेणी क्लासिफायर, एक फ्रॉड स्कोरर जो OCR संकेत, परसेप्चुअल-हैश डुप्लिकेट मिलान और MobileNetV2 छेड़छाड़ नेटवर्क को जोड़ता है, और Isolation-Forest खर्च-विसंगति जाँच।',
            s4t: '🎁 इनाम और अनुशंसा', s4d: 'पहले से क्लेम की गई रसीद — चाहे आपके द्वारा या किसी और के द्वारा — यहीं अस्वीकार कर दी जाती है और कोई अंक नहीं मिलते। अन्यथा पॉइंट्स इंजन ₹100 = 1 पॉइंट की गणना करता है, जो खर्च श्रेणी, उपयोगकर्ता टियर और स्ट्रीक के अनुसार समायोजित होता है, और पॉइंट्स, फ्रॉड निर्णय तथा वैयक्तिकृत ऑफ़र Firestore में लिखे जाकर आपकी स्क्रीन पर लौटाए जाते हैं।',
            archTitle: 'पर्दे के पीछे — आर्किटेक्चर',
            archLead: 'तीन-स्तरीय डिज़ाइन AI/ML परत को ऐप लॉजिक से अलग रखता है, ताकि हर हिस्सा स्वतंत्र रूप से विकसित हो सके।',
            c1t: 'फ्रंटएंड', c1d: '4-स्टेप स्टेपर वाला सिंगल-पेज ऐप। अपलोड, ऑथ UI और लाइव परिणाम रेंडरिंग संभालता है।',
            c2t: 'बैकएंड API', c2d: 'पाइपलाइन का समन्वय: JWT ऑथ, रिवॉर्ड और क्लेम लॉजिक, और डेटाबेस से संवाद।',
            c3t: 'ML माइक्रोसर्विस', c3d: 'एक पृथक Python सेवा जो OCR और हर ML मॉडल को <code>/ml/*</code> एंडपॉइंट्स के पीछे होस्ट करती है।',
            c4t: 'डेटा और AI', c4d: 'Firestore उपयोगकर्ता, रसीदें, पॉइंट और फ्रॉड स्कोर संग्रहीत करता है; Gemini OCR एक्सट्रैक्शन चलाता है।',
            requestFlow: 'अनुरोध प्रवाह',
            trust1: '🏛️ <strong>BITS Pilani</strong> Digital',
            trust2: '🤖 <strong>Google Gemini AI</strong> द्वारा संचालित',
            trust3: '👥 ग्रुप 120 — <strong>टीम ' + ARAJ + '</strong>'
        },

        ml: {
            badge: 'ക്യാപ്‌സ്റ്റോൺ പ്രോജക്ട് • BITS PILANI DIGITAL',
            heroTitle: 'ഓരോ ബില്ലും റിവാർഡുകളാക്കി മാറ്റൂ',
            heroSubtitle: 'Gemini AI പ്രവർത്തിപ്പിക്കുന്ന ഒരു ബുദ്ധിപരമായ ക്യാപ്‌സ്റ്റോൺ പ്രോജക്ട്. ബില്ലുകൾ സ്കാൻ ചെയ്യൂ, പോയിന്റുകൾ നേടൂ, റീട്ടെയിൽ റിവാർഡുകളുടെ ഭാവി അനുഭവിക്കൂ.',
            btnSignIn: 'സൈൻ ഇൻ / സൈൻ അപ്പ്',
            btnGuest: 'അതിഥിയായി കാണുക',
            feat1t: 'തൽക്ഷണ OCR', feat1d: 'AI സെക്കൻഡുകൾക്കുള്ളിൽ ലൈൻ-ഐറ്റം ഡാറ്റ വേർതിരിക്കുന്നു',
            feat2t: 'തട്ടിപ്പ് കണ്ടെത്തൽ', feat2d: 'ഓരോ സ്കാനിലും ഡ്യൂപ്ലിക്കേറ്റ്, കൃത്രിമം, അപാകത പരിശോധന',
            feat3t: 'സ്മാർട്ട് മൾട്ടിപ്ലയറുകൾ', feat3d: 'വിഭാഗം & സ്ട്രീക്ക് അടിസ്ഥാന റിവാർഡുകൾ',
            feat4t: 'സ്വകാര്യത ആദ്യം', feat4d: 'എന്റർപ്രൈസ്-ഗ്രേഡ് ഡാറ്റ കൈകാര്യം',
            learnMore: 'കൂടുതൽ അറിയുക',
            whatT: 'ഈ സിസ്റ്റം എന്താണ്?',
            whatD: 'ബിൽ സ്കാനിംഗ് റിവാർഡ് AI സിസ്റ്റം എന്നത് റീട്ടെയിൽ രസീതുകൾ ഡിജിറ്റൈസ് ചെയ്യാനും വിശകലനം ചെയ്യാനും പ്രോസസ് ചെയ്യാനും അത്യാധുനിക Gemini AI ഉപയോഗിക്കുന്ന ഒരു ഫൈനൽ-ഇയർ ക്യാപ്‌സ്റ്റോൺ പ്രോജക്ടാണ്. ഇത് തൽക്ഷണം ലൈൻ-ഐറ്റം ഡാറ്റ വേർതിരിക്കുന്നു, ഡ്യൂപ്ലിക്കേറ്റ് സ്കാനുകൾ ചലനാത്മകമായി പരിശോധിക്കുന്നു, ഷോപ്പിംഗ് വിഭാഗങ്ങളും ഉപയോക്തൃ സ്ട്രീക്ക് സ്വഭാവവും അടിസ്ഥാനമാക്കി ബുദ്ധിപരമായ റിവാർഡ് മൾട്ടിപ്ലയറുകൾ കണക്കാക്കുന്നു. സ്വകാര്യതയും എന്റർപ്രൈസ്-തല ഡാറ്റ കൈകാര്യവും ഉറപ്പാക്കിക്കൊണ്ട് ഇത് സാധാരണ ഷോപ്പിംഗിനെ ആകർഷകവും ഗെയിമിഫൈഡുമായ അനുഭവമാക്കി മാറ്റുന്നു.',
            teamT: ARAJ + ' ടീം ആരാണ്?',
            teamD: ARAJ + ' ടീമിൽ (ഗ്രൂപ്പ് 120) BITS Pilani Digital-ലെ നാല് ഉത്സാഹികളായ B.Sc. കമ്പ്യൂട്ടർ സയൻസ് വിദ്യാർത്ഥികൾ ഉൾപ്പെടുന്നു. ഈ സുരക്ഷിതവും ചലനാത്മകവും അത്യാധുനികവുമായ റിവാർഡ്സ് ഇൻഫ്രാസ്ട്രക്ചർ ഞങ്ങൾ രൂപകൽപ്പന ചെയ്തു.',
            role1: 'ടീം ലീഡ് & ലീഡ് ഡെവലപ്പർ',
            role2: 'തട്ടിപ്പ് കണ്ടെത്തൽ & QA',
            role3: 'ML ഗവേഷണം & ഡാറ്റാസെറ്റ്',
            role4: 'ഡാറ്റ ലേബലിംഗ് & ഡോക്യുമെന്റേഷൻ',
            aboutTitle: 'ഈ ക്യാപ്‌സ്റ്റോൺ പ്രോജക്ടിനെക്കുറിച്ച്',
            aboutIntro: 'ഇത് ARAJ ടീമിന്റെ (ഗ്രൂപ്പ് 120) ഫൈനൽ-ഇയർ <strong>ക്യാപ്‌സ്റ്റോൺ പ്രോജക്ട്</strong> ആണ്, B.Sc. കമ്പ്യൂട്ടർ സയൻസ്, <strong>BITS Pilani Digital</strong>, <strong>പ്രൊഫ. ഉമ ശങ്കര റാവു</strong>-വിന്റെ മാർഗനിർദേശത്തിൽ. OCR, തട്ടിപ്പ് കണ്ടെത്തൽ, ചെലവ് വർഗ്ഗീകരണം, വ്യക്തിഗത റിവാർഡുകൾ എന്നിവ ഉൾപ്പെടുന്ന ഒരു എൻഡ്-ടു-എൻഡ് രസീത്-സ്കാനിംഗ് റിവാർഡ് പൈപ്പ്‌ലൈൻ ഒരു <strong>അക്കാദമിക് പഠനമായി</strong> ഇത് പ്രദർശിപ്പിക്കുന്നു, വാണിജ്യ ഉൽപ്പന്നമായല്ല.',
            scopeTitle: 'വ്യാപ്തിയും നിലവിലെ അവസ്ഥയും:',
            scope1: 'OCR ലൈവ് ആണ് (Google Gemini 2.5 Flash).',
            scope2: 'അഞ്ച് ML മോഡലുകളും പരിശീലിപ്പിച്ച്, സംയോജിപ്പിച്ച്, പൂർണ്ണമായി പരിശോധിച്ചു — വിഭാഗം, തട്ടിപ്പ്, കൃത്രിമം, അപാകത, ശുപാർശ.',
            scope3: 'റിവാർഡ്, ക്ലെയിം, അനലിറ്റിക്‌സ് ലോജിക് ലൈവ് ബാക്കെൻഡ് + Firestore-ൽ പ്രവർത്തിക്കുന്നു.',
            scope4: 'പ്രദർശനത്തിനും പഠനത്തിനും വേണ്ടി നിർമ്മിച്ചത് — പ്രൊഡക്ഷൻ-ഹാർഡൻഡ് അല്ല.',
            btnCapstoneRepo: '📦 ക്യാപ്‌സ്റ്റോൺ റിപ്പോസിറ്ററി',
            btnPocRepo: '🔬 ഫേസ് 3 PoC · സ്റ്റഡി പ്രോജക്ട്',
            hiwTitle: 'എങ്ങനെ പ്രവർത്തിക്കുന്നു',
            hiwLead: 'ഒരു രസീത് ഫോട്ടോയിൽ നിന്ന് സെക്കൻഡുകൾക്കുള്ളിൽ റിവാർഡ് പോയിന്റുകളിലേക്ക് — ഇതാ പൂർണ്ണ യാത്രയും അതിനെ പ്രവർത്തിപ്പിക്കുന്ന ആർക്കിടെക്ചറും.',
            s1t: '📤 അപ്‌ലോഡ്', s1d: 'നിങ്ങൾ ബ്രൗസറിൽ ഒരു രസീത് ചിത്രം ഇടുന്നു. സിംഗിൾ-പേജ് ഫ്രണ്ട്എൻഡ് അതിനെ ഒരു ആധികാരിക (JWT) അഭ്യർത്ഥനയിലൂടെ ബാക്കെൻഡിലേക്ക് അയയ്ക്കുന്നു.',
            s2t: '🔍 എക്‌സ്‌ട്രാക്റ്റ് — OCR', s2d: 'ബാക്കെൻഡ് ചിത്രം ML മൈക്രോസർവീസിലേക്ക് കൈമാറുന്നു, അവിടെ 5-ലെയർ OCR പൈപ്പ്‌ലൈൻ പ്രവർത്തിക്കുന്നു: ഏതെങ്കിലും AI ചെലവിനു മുൻപ് വായിക്കാനാകാത്ത ചിത്രങ്ങൾ നിരസിക്കുന്ന ഷാർപ്പ്നെസ് പരിശോധന, റേറ്റ്-ലിമിറ്റ് ഗേറ്റ്, Google Gemini 2.5 Flash എക്‌സ്‌ട്രാക്ഷൻ, മോഡൽ ഫോൾബാക്ക്, കൈയെഴുത്ത് മാറ്റങ്ങൾ അടയാളപ്പെടുത്തുന്ന പിക്‌സൽ-സാന്ദ്രത സ്കാൻ.',
            s3t: '🧠 വർഗ്ഗീകരണവും കണ്ടെത്തലും', s3d: 'വേർതിരിച്ച ഫീൽഡുകൾ ML മോഡലുകളിലൂടെ കടന്നുപോകുന്നു — TF-IDF + Random Forest വിഭാഗ ക്ലാസിഫയർ, OCR സൂചനകളും പെർസെപ്ച്വൽ-ഹാഷ് ഡ്യൂപ്ലിക്കേറ്റ് പൊരുത്തവും MobileNetV2 കൃത്രിമ ശൃംഖലയും സംയോജിപ്പിക്കുന്ന തട്ടിപ്പ് സ്കോറർ, Isolation-Forest ചെലവ്-അപാകത പരിശോധന.',
            s4t: '🎁 റിവാർഡും ശുപാർശയും', s4d: 'ഇതിനകം ക്ലെയിം ചെയ്ത ഒരു രസീത് — നിങ്ങളാലോ മറ്റാരെങ്കിലുമോ — ഇവിടെ നിരസിക്കപ്പെടും, പോയിന്റുകളൊന്നും ലഭിക്കില്ല. അല്ലാത്തപക്ഷം പോയിന്റ്സ് എഞ്ചിൻ ₹100 = 1 പോയിന്റ് കണക്കാക്കുന്നു, ചെലവ് വിഭാഗം, ഉപയോക്തൃ ടയർ, സ്ട്രീക്ക് എന്നിവയനുസരിച്ച് ക്രമീകരിച്ച്, പോയിന്റുകളും തട്ടിപ്പ് വിധിയും വ്യക്തിഗത ഓഫറുകളും Firestore-ൽ എഴുതി നിങ്ങളുടെ സ്ക്രീനിലേക്ക് തിരികെ നൽകുന്നു.',
            archTitle: 'അണിയറയിൽ — ആർക്കിടെക്ചർ',
            archLead: 'മൂന്ന്-തല രൂപകൽപ്പന AI/ML ലെയറിനെ ആപ്പ് ലോജിക്കിൽ നിന്ന് വേർതിരിക്കുന്നു, അതിനാൽ ഓരോ ഭാഗവും സ്വതന്ത്രമായി വികസിക്കാം.',
            c1t: 'ഫ്രണ്ട്എൻഡ്', c1d: '4-സ്റ്റെപ്പ് സ്റ്റെപ്പറുള്ള സിംഗിൾ-പേജ് ആപ്പ്. അപ്‌ലോഡ്, ഓത്ത് UI, ലൈവ് ഫലം റെൻഡറിംഗ് കൈകാര്യം ചെയ്യുന്നു.',
            c2t: 'ബാക്കെൻഡ് API', c2d: 'പൈപ്പ്‌ലൈൻ ഏകോപിപ്പിക്കുന്നു: JWT ഓത്ത്, റിവാർഡ് & ക്ലെയിം ലോജിക്, ഡാറ്റാബേസുമായി സംവദിക്കുന്നു.',
            c3t: 'ML മൈക്രോസർവീസ്', c3d: 'OCR-ഉം എല്ലാ ML മോഡലുകളും <code>/ml/*</code> എൻഡ്‌പോയിന്റുകൾക്ക് പിന്നിൽ ഹോസ്റ്റ് ചെയ്യുന്ന ഒറ്റപ്പെട്ട Python സേവനം.',
            c4t: 'ഡാറ്റയും AI-യും', c4d: 'Firestore ഉപയോക്താക്കൾ, രസീതുകൾ, പോയിന്റുകൾ, ഫ്രോഡ് സ്കോറുകൾ സംഭരിക്കുന്നു; Gemini OCR എക്‌സ്‌ട്രാക്ഷൻ പ്രവർത്തിപ്പിക്കുന്നു.',
            requestFlow: 'അഭ്യർത്ഥന ഒഴുക്ക്',
            trust1: '🏛️ <strong>BITS Pilani</strong> Digital',
            trust2: '🤖 <strong>Google Gemini AI</strong> പ്രവർത്തിപ്പിക്കുന്നു',
            trust3: '👥 ഗ്രൂപ്പ് 120 — <strong>' + ARAJ + ' ടീം</strong>'
        },

        zh: {
            badge: '毕业设计项目 • BITS PILANI DIGITAL',
            heroTitle: '把每一张收据变成奖励',
            heroSubtitle: '由 Gemini AI 驱动的智能毕业设计项目。扫描账单、赚取积分，体验零售奖励的未来。',
            btnSignIn: '登录 / 注册',
            btnGuest: '以访客身份浏览',
            feat1t: '即时 OCR', feat1d: 'AI 数秒内提取逐项数据',
            feat2t: '欺诈检测', feat2d: '每次扫描均检测重复、篡改与异常',
            feat3t: '智能倍率', feat3d: '基于类别与连续打卡的奖励',
            feat4t: '隐私优先', feat4d: '企业级数据处理',
            learnMore: '了解更多',
            whatT: '这是什么系统？',
            whatD: '账单扫描奖励 AI 系统是一个毕业设计项目，利用前沿的 Gemini AI 对零售收据进行数字化、分析和处理。它可即时提取逐项数据，动态校验重复扫描，并根据购物类别与用户连续打卡行为计算智能奖励倍率。它在确保隐私与企业级数据处理的同时，将日常购物转变为富有吸引力的游戏化体验。',
            teamT: ARAJ + ' 团队是谁？',
            teamD: ARAJ + ' 团队（第 120 组）由来自 BITS Pilani Digital 的四名充满热情的计算机科学本科生组成。我们打造了这套安全、动态且先进的奖励基础设施。',
            role1: '团队负责人兼主开发',
            role2: '欺诈检测与质量保证',
            role3: '机器学习研究与数据集',
            role4: '数据标注与文档',
            aboutTitle: '关于本毕业设计项目',
            aboutIntro: '这是 ARAJ 团队（第 120 组）的<strong>毕业设计项目</strong>，计算机科学本科，隶属 <strong>BITS Pilani Digital</strong>，由 <strong>Uma Sankara Rao 教授</strong>指导。它作为一项<strong>学术研究</strong>而非商业产品，展示了端到端的收据扫描奖励流程——OCR、欺诈检测、消费分类与个性化奖励。',
            scopeTitle: '范围与当前状态：',
            scope1: 'OCR 已上线（Google Gemini 2.5 Flash）。',
            scope2: '五个机器学习模型均已训练、集成并完成端到端验证：分类、欺诈、篡改、异常与推荐。',
            scope3: '奖励、兑换与分析逻辑已在实时后端 + Firestore 上运行。',
            scope4: '为演示与研究而构建——未做生产级加固。',
            btnCapstoneRepo: '📦 毕业设计代码库',
            btnPocRepo: '🔬 第 3 阶段 PoC · 学习项目',
            hiwTitle: '工作原理',
            hiwLead: '从一张收据照片到数秒内的奖励积分——这是完整流程以及支撑它的架构。',
            s1t: '📤 上传', s1d: '你在浏览器中放入一张收据图片。单页前端通过带认证（JWT）的请求将其发送到后端。',
            s2t: '🔍 提取 — OCR', s2d: '后端将图片转发到 ML 微服务，运行五层 OCR 流程：清晰度检测（在任何 AI 调用之前拒绝无法识别的照片）、限流闸门、Google Gemini 2.5 Flash 提取、模型回退，以及标记手写改动的像素密度扫描。',
            s3t: '🧠 分类与检测', s3d: '提取的字段流经 ML 模型——TF-IDF + Random Forest 类别分类器、结合 OCR 信号、感知哈希重复匹配与 MobileNetV2 篡改网络的欺诈评分器，以及 Isolation-Forest 消费异常检测。',
            s4t: '🎁 奖励与推荐', s4d: '已被领取过的收据——无论是你还是他人——都会在此被拒绝，不会获得任何积分。否则积分引擎按 ₹100 = 1 分计算，并根据消费类别、用户等级与连续打卡进行调整，积分、欺诈判定与个性化优惠写入 Firestore 并返回到你的屏幕。',
            archTitle: '幕后 — 架构',
            archLead: '三层设计将 AI/ML 层与应用逻辑隔离，使各部分能够独立演进。',
            c1t: '前端', c1d: '带四步步骤条的单页应用。处理上传、认证界面与实时结果渲染。',
            c2t: '后端 API', c2d: '编排整个流程：JWT 认证、奖励与兑换逻辑，并与数据库通信。',
            c3t: 'ML 微服务', c3d: '独立的 Python 服务，在 <code>/ml/*</code> 端点后托管 OCR 与全部 ML 模型。',
            c4t: '数据与 AI', c4d: 'Firestore 存储用户、收据、积分与欺诈分数；Gemini 驱动 OCR 提取。',
            requestFlow: '请求流程',
            trust1: '🏛️ <strong>BITS Pilani</strong> Digital',
            trust2: '🤖 由 <strong>Google Gemini AI</strong> 驱动',
            trust3: '👥 第 120 组 — <strong>' + ARAJ + ' 团队</strong>'
        }
    };

    function applyLanguage(lang) {
        var dict = T[lang] || T.en;
        document.querySelectorAll('[data-i18n]').forEach(function (el) {
            var v = dict[el.getAttribute('data-i18n')];
            if (v != null) el.textContent = v;
        });
        document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
            var v = dict[el.getAttribute('data-i18n-html')];
            if (v != null) el.innerHTML = v;
        });
        var section = document.getElementById('section-auth');
        var rtl = (lang === 'ar');
        if (section) {
            section.setAttribute('dir', rtl ? 'rtl' : 'ltr');
            section.classList.toggle('rtl', rtl);
        }
        document.documentElement.lang = lang;
        document.querySelectorAll('.lang-option').forEach(function (b) {
            b.classList.toggle('active', b.getAttribute('data-lang') === lang);
        });
        try { localStorage.setItem('lang', lang); } catch (e) { }
    }
    window.applyLanguage = applyLanguage;

    document.addEventListener('DOMContentLoaded', function () {
        var fab = document.getElementById('lang-fab');
        var drawer = document.getElementById('lang-drawer');
        if (!fab || !drawer) return;

        fab.addEventListener('click', function (e) {
            e.stopPropagation();
            drawer.classList.toggle('hidden');
        });
        drawer.querySelectorAll('.lang-option').forEach(function (opt) {
            opt.addEventListener('click', function () {
                applyLanguage(opt.getAttribute('data-lang'));
                drawer.classList.add('hidden');
            });
        });
        document.addEventListener('click', function (e) {
            if (!drawer.contains(e.target) && e.target !== fab) drawer.classList.add('hidden');
        });

        // The switcher lives at body level (so no container can clip it);
        // mirror the landing section's visibility onto it so it only shows
        // on the landing page and hides once the user is logged in.
        var langSwitch = document.getElementById('lang-switch');
        var authSection = document.getElementById('section-auth');
        function syncSwitchVisibility() {
            if (!langSwitch || !authSection) return;
            langSwitch.classList.toggle('hidden', authSection.classList.contains('hidden'));
        }
        syncSwitchVisibility();
        if (authSection && window.MutationObserver) {
            new MutationObserver(syncSwitchVisibility).observe(authSection, {
                attributes: true, attributeFilter: ['class']
            });
        }

        var saved = null;
        try { saved = localStorage.getItem('lang'); } catch (e) { }
        // English is the default HTML (with the hero typing animation); only
        // apply a translation on load for the non-default languages.
        if (saved && T[saved] && saved !== 'en') applyLanguage(saved);
    });
})();
