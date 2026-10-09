/* ==========================================================
   FloatingTextbook AI — Comprehensive Client-Side Application
   ==========================================================
   Connects UI templates to the Data Science & AI backend:
   1. State Management & API Communication
   2. Document Upload & Smart Textbook Reader
   3. Interactive Parameter Simulations (Faraday & Finance Labs)
   4. Adaptive Quiz Engine with Persistent Logging
   5. Explainable Learning Gap & Mastery Visualizer
   6. Dynamic Personalized Study Planner
   7. Socratic AI Companion with Grounded Citations
   8. Mission-Based Learning Challenges
   ========================================================== */

(function () {
  'use strict';

  const API_BASE = ''; // Same origin (FastAPI backend)

  /* ----------------------------------------------------------
     STATE
     ---------------------------------------------------------- */
  const state = {
    currentPage: 'home',
    learnerId: 'learner-001',
    tutorMode: 'explain',
    documents: [],
    topics: [],
    quizzes: [],
    activeQuiz: null,
    activeQuestionIdx: 0,
    quizUserAnswers: {},
    quizHintsUsed: 0,
    gaps: [],
    studyPlan: [],
    analytics: null,
    missions: [],
    faraday: {
      turns: 200,
      speed: 4.0,
      field: 0.8,
      area: 0.05,
      stage: 1,
      animId: null
    },
    finance: {
      principal: 5000,
      rate: 0.08,
      time: 10,
      compounding: 12
    }
  };

  /* ----------------------------------------------------------
     DOM REFERENCES
     ---------------------------------------------------------- */
  const mainContent = document.getElementById('mainContent');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const hamburgerBtn = document.getElementById('hamburgerBtn');

  /* ==========================================================
     API CLIENT HELPERS
     ========================================================== */
  async function apiFetch(endpoint, options = {}) {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `HTTP Error ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.warn(`[FloatingApp API] Error fetching ${endpoint}:`, err.message);
      throw err;
    }
  }

  /* ==========================================================
     PAGE ROUTING
     ========================================================== */
  function renderPage(pageId) {
    const template = document.getElementById('tpl-' + pageId);
    if (!template) {
      console.warn(`Template tpl-${pageId} not found.`);
      return;
    }

    // Cancel any running simulation animations from previous page
    if (state.faraday.animId) {
      cancelAnimationFrame(state.faraday.animId);
      state.faraday.animId = null;
    }

    mainContent.innerHTML = '';
    mainContent.appendChild(template.content.cloneNode(true));
    state.currentPage = pageId;
    mainContent.focus();

    // Re-bind interactions scoped to page
    switch (pageId) {
      case 'home':
        initHomePage();
        break;
      case 'my-learning':
        initMyLearningPage();
        break;
      case 'upload':
        initUploadPage();
        break;
      case 'explore':
        initExplorePage();
        break;
      case 'interactive-labs':
        initInteractiveLabsPage();
        break;
      case 'practice':
        initPracticePage();
        break;
      case 'learning-gaps':
        initLearningGapsPage();
        break;
      case 'revision':
        initStudyPlanPage();
        break;
      case 'mastery':
        initAnalyticsMasteryPage();
        break;
      case 'missions':
        initMissionsPage();
        break;
      case 'ai-teacher':
        initAITeacherPage();
        break;
      case 'settings':
        initSettingsPage();
        break;
      case 'doubt-solving':
        initDoubtPage();
        break;
    }

    animateProgressBars();
  }

  function setActiveNav(pageId) {
    document.querySelectorAll('.nav-item').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.page === pageId);
    });
    document.querySelectorAll('.bnav-item').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.page === pageId);
    });
  }

  function goToPage(pageId) {
    renderPage(pageId);
    setActiveNav(pageId);
    closeMobileSidebar();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  window.FloatingApp = { goToPage };

  /* ==========================================================
     MOBILE SIDEBAR
     ========================================================== */
  function openMobileSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('visible');
    hamburgerBtn.setAttribute('aria-expanded', 'true');
  }
  function closeMobileSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('visible');
    hamburgerBtn.setAttribute('aria-expanded', 'false');
  }
  function toggleMobileSidebar() {
    if (sidebar.classList.contains('open')) {
      closeMobileSidebar();
    } else {
      openMobileSidebar();
    }
  }

  function animateProgressBars() {
    const bars = mainContent.querySelectorAll('.mastery-fill, .inline-progress-fill');
    bars.forEach((bar) => {
      const target = bar.style.width;
      bar.style.width = '0%';
      requestAnimationFrame(() => {
        setTimeout(() => {
          bar.style.width = target;
        }, 50);
      });
    });
  }

  /* ==========================================================
     1. HOME / DASHBOARD PAGE
     ========================================================== */
  async function initHomePage() {
    const learningInput = document.getElementById('learningInput');
    const sendBtn = document.getElementById('sendBtn');
    const aiResponse = document.getElementById('aiResponse');
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceStatus = document.getElementById('voiceStatus');

    // Fetch live dashboard analytics and gap data
    try {
      const dashboard = await apiFetch('/api/analytics/dashboard');
      state.analytics = dashboard.eda;
      state.gaps = dashboard.active_gaps;

      // Update personalized insight banner on home page with real detected gap!
      const insightObs = document.querySelector('.insight-observation');
      const insightRec = document.querySelector('.insight-recommendation');
      if (state.gaps && state.gaps.length > 0) {
        const topGap = state.gaps[0];
        if (insightObs) insightObs.textContent = topGap.explanation;
        if (insightRec) insightRec.textContent = topGap.suggested_remedy;
      }
    } catch (e) {
      console.warn('Dashboard fetch notice:', e);
    }

    // Send question from Home page to Socratic backend
    const handleHomeSend = async () => {
      const query = (learningInput.value || '').trim();
      if (!query) return;

      aiResponse.hidden = false;
      aiResponse.innerHTML = '<p class="ar-intro"><em>✦ Generating grounded textbook explanation…</em></p>';

      try {
        const result = await apiFetch('/api/tutor/chat', {
          method: 'POST',
          body: JSON.stringify({ query: query, mode: 'explain' })
        });

        renderTutorResponse(result, aiResponse);
      } catch (err) {
        aiResponse.innerHTML = `<p class="ar-intro" style="color:var(--coral-dark);">Could not connect: ${escapeHTML(err.message)}</p>`;
      }
    };

    if (sendBtn) sendBtn.addEventListener('click', handleHomeSend);
    if (learningInput) {
      learningInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleHomeSend();
        }
      });
    }

    // Quick prompt chips
    document.querySelectorAll('.prompt-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        learningInput.value = chip.textContent.trim();
        handleHomeSend();
      });
    });

    // Upload Chips on home page trigger the real Upload page
    document.querySelectorAll('.upload-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        goToPage('upload');
      });
    });

    // Voice simulation
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => {
        startVoiceInput(voiceBtn, voiceStatus, learningInput);
      });
    }

    // Feature card click actions
    const featureCards = document.querySelectorAll('.feature-card');
    if (featureCards[0]) featureCards[0].addEventListener('click', () => goToPage('explore'));
    if (featureCards[1]) featureCards[1].addEventListener('click', () => goToPage('interactive-labs'));
    if (featureCards[2]) featureCards[2].addEventListener('click', () => goToPage('practice'));
    if (featureCards[3]) featureCards[3].addEventListener('click', () => goToPage('mastery'));

    // Topic card actions
    document.querySelectorAll('.topic-action').forEach((btn) => {
      btn.addEventListener('click', () => goToPage('explore'));
    });

    const insightBtn = document.querySelector('.insight-btn');
    if (insightBtn) insightBtn.addEventListener('click', () => goToPage('practice'));
  }

  /* ==========================================================
     2. MY TEXTBOOKS & MATERIALS
     ========================================================== */
  async function initMyLearningPage() {
    const container = document.getElementById('textbooksContainer');
    if (!container) return;

    container.innerHTML = '<p class="muted">Loading indexed textbooks…</p>';

    try {
      const docs = await apiFetch('/api/documents');
      state.documents = docs;

      if (!docs || docs.length === 0) {
        container.innerHTML = `
          <div class="generic-block wide" style="text-align:center; padding:40px;">
            <p class="muted">No textbooks uploaded yet.</p>
            <button class="mini-btn mini-btn-primary" style="margin-top:14px;" onclick="window.FloatingApp.goToPage('upload')">⇪ Upload First Textbook</button>
          </div>
        `;
        return;
      }

      container.innerHTML = docs.map((doc) => `
        <article class="generic-block" style="display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
              <span class="pill-badge pill-low">${escapeHTML(doc.subject)}</span>
              <span class="muted" style="font-size:12px;">${escapeHTML(doc.status)}</span>
            </div>
            <h2 style="margin-top:12px; font-size:18px;">${escapeHTML(doc.title)}</h2>
            <p class="muted" style="font-size:13px; margin-top:6px;">${escapeHTML(doc.summary || '')}</p>
            <p style="font-size:12px; color:var(--muted-text); margin-top:10px;">
              📄 ${doc.page_count} Pages · 🧩 ${doc.chunk_count || 7} Indexed Chunks
            </p>
          </div>
          <div style="display:flex; gap:10px; margin-top:18px;">
            <button class="mini-btn mini-btn-primary" onclick="window.FloatingApp.goToPage('explore')">Read Chunks →</button>
            <button class="mini-btn" onclick="window.FloatingApp.goToPage('practice')">Take Quiz</button>
          </div>
        </article>
      `).join('');
    } catch (err) {
      container.innerHTML = `<p class="muted" style="color:var(--coral-dark);">Failed to load textbooks: ${escapeHTML(err.message)}</p>`;
    }
  }

  /* ==========================================================
     3. UPLOAD MATERIAL
     ========================================================== */
  function initUploadPage() {
    const dropZone = document.getElementById('mainDropZone');
    const fileInput = document.getElementById('primaryFileInput');
    const startBtn = document.getElementById('startUploadBtn');
    const progressBox = document.getElementById('uploadProgressBox');
    const resultCard = document.getElementById('uploadResultCard');
    const subjectSelect = document.getElementById('uploadSubject');

    let selectedFile = null;

    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files[0]) {
        handleFileSelect(fileInput.files[0]);
      }
    });

    function handleFileSelect(file) {
      selectedFile = file;
      dropZone.querySelector('.drop-title').textContent = `Selected: ${file.name}`;
      dropZone.querySelector('.drop-sub').textContent = `Size: ${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to parse.`;
    }

    if (startBtn) {
      startBtn.addEventListener('click', async () => {
        if (!selectedFile) {
          alert('Please drag & drop or select a textbook PDF/TXT file first.');
          return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('subject', subjectSelect.value);

        progressBox.style.display = 'block';
        resultCard.style.display = 'none';

        try {
          const res = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
          });

          if (!res.ok) {
            const errJson = await res.json().catch(() => ({}));
            throw new Error(errJson.detail || 'Upload failed');
          }

          const data = await res.json();
          progressBox.style.display = 'none';
          resultCard.style.display = 'block';
          resultCard.innerHTML = `
            <h3 style="color:#2F4D25; margin-bottom:6px;">✓ Textbook Successfully Processed & Indexed!</h3>
            <p><strong>Title:</strong> ${escapeHTML(data.title)}</p>
            <p><strong>Pages:</strong> ${data.page_count} pages extracted | <strong>Chunks:</strong> ${data.chunks_extracted} indexed</p>
            <div style="margin-top:14px; display:flex; gap:12px;">
              <button class="mini-btn mini-btn-primary" onclick="window.FloatingApp.goToPage('explore')">Read & Explore Topics →</button>
              <button class="mini-btn" onclick="window.FloatingApp.goToPage('practice')">Take Diagnostic Quiz</button>
            </div>
          `;
        } catch (err) {
          progressBox.style.display = 'none';
          resultCard.style.display = 'block';
          resultCard.className = 'hint-box';
          resultCard.innerHTML = `<strong>Upload Error:</strong> ${escapeHTML(err.message)}`;
        }
      });
    }
  }

  /* ==========================================================
     4. EXPLORE & READ TEXTBOOK
     ========================================================== */
  async function initExplorePage() {
    const topicListEl = document.getElementById('exploreTopicList');
    const readerPane = document.getElementById('chunkReaderContent');
    if (!topicListEl || !readerPane) return;

    topicListEl.innerHTML = '<li class="muted">Loading topics…</li>';

    try {
      const topics = await apiFetch('/api/topics');
      state.topics = topics;

      if (!topics || topics.length === 0) {
        topicListEl.innerHTML = '<li class="muted">No topics found.</li>';
        return;
      }

      topicListEl.innerHTML = topics.map((t, idx) => `
        <li style="cursor:pointer;" class="explore-topic-item ${idx === 0 ? 'selected-topic' : ''}" data-topic-id="${t.id}">
          <div style="display:flex; flex-direction:column; gap:2px;">
            <span style="font-weight:600;">${escapeHTML(t.title)}</span>
            <span class="muted" style="font-size:12px;">${escapeHTML(t.subject)} · ${escapeHTML(t.page_range || 'p. 1')}</span>
          </div>
          <span class="pill-tag ${t.mastery_status === 'Strong Mastery' ? 'pill-good' : (t.mastery_status === 'Needs Revision' ? 'pill-warn' : '')}">
            ${t.mastery_estimate ? Math.round(t.mastery_estimate * 100) + '%' : 'Untested'}
          </span>
        </li>
      `).join('');

      // Auto load first topic
      loadTopicChunks(topics[0].id);

      document.querySelectorAll('.explore-topic-item').forEach((item) => {
        item.addEventListener('click', () => {
          document.querySelectorAll('.explore-topic-item').forEach((i) => i.classList.remove('selected-topic'));
          item.classList.add('selected-topic');
          loadTopicChunks(item.dataset.topicId);
        });
      });
    } catch (err) {
      topicListEl.innerHTML = `<li class="muted" style="color:var(--coral-dark);">${escapeHTML(err.message)}</li>`;
    }

    async function loadTopicChunks(topicId) {
      readerPane.innerHTML = '<p class="muted">Loading grounded textbook chunks…</p>';
      try {
        const data = await apiFetch(`/api/topics/${topicId}/chunks`);
        const topic = data.topic;
        const chunks = data.chunks;

        let chunksHtml = `
          <div style="border-bottom:1.5px solid var(--border); padding-bottom:16px; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="pill-badge pill-low">${escapeHTML(topic.subject)}</span>
              <span class="muted" style="font-size:12.5px;">${escapeHTML(topic.page_range || '')}</span>
            </div>
            <h1 style="font-size:26px; color:var(--burgundy-dark); margin-top:8px;">${escapeHTML(topic.title)}</h1>
            <p class="muted" style="margin-top:6px;">${escapeHTML(topic.summary || '')}</p>
            <div style="display:flex; gap:12px; margin-top:14px;">
              <button class="mini-btn mini-btn-primary" onclick="window.FloatingApp.goToPage('interactive-labs')">⚗ Open Concept Lab</button>
              <button class="mini-btn" onclick="window.FloatingApp.goToPage('practice')">✎ Practice Quiz</button>
              <button class="mini-btn" onclick="window.FloatingApp.goToPage('ai-teacher')">✦ Ask Socratic AI</button>
            </div>
          </div>
        `;

        if (!chunks || chunks.length === 0) {
          chunksHtml += '<p class="muted">No direct text chunks recorded for this topic yet.</p>';
        } else {
          chunksHtml += chunks.map((c) => `
            <article class="citation-card" style="margin-bottom:16px; padding:16px 20px;">
              <div class="citation-header">
                <span>📖 Page ${c.page_number} — ${escapeHTML(c.heading || 'Textbook Excerpt')}</span>
              </div>
              <p style="font-size:14.5px; line-height:1.6; color:var(--charcoal); margin-top:8px;">
                ${escapeHTML(c.content)}
              </p>
            </article>
          `).join('');
        }

        readerPane.innerHTML = chunksHtml;
      } catch (err) {
        readerPane.innerHTML = `<p class="muted" style="color:var(--coral-dark);">Error: ${escapeHTML(err.message)}</p>`;
      }
    }
  }

  /* ==========================================================
     5. INTERACTIVE SIMULATION LABS
     ========================================================== */
  function initInteractiveLabsPage() {
    const tabFaraday = document.getElementById('tabLabFaraday');
    const tabFinance = document.getElementById('tabLabFinance');
    const secFaraday = document.getElementById('labFaradaySection');
    const secFinance = document.getElementById('labFinanceSection');

    if (!tabFaraday || !tabFinance) return;

    tabFaraday.addEventListener('click', () => {
      tabFaraday.classList.add('active');
      tabFinance.classList.remove('active');
      secFaraday.style.display = 'block';
      secFinance.style.display = 'none';
      renderFaradaySimulation();
    });

    tabFinance.addEventListener('click', () => {
      tabFinance.classList.add('active');
      tabFaraday.classList.remove('active');
      secFaraday.style.display = 'none';
      secFinance.style.display = 'block';
      renderFinanceSimulation();
    });

    // ---------------- Faraday Controls ----------------
    const sliderTurns = document.getElementById('sliderTurns');
    const sliderSpeed = document.getElementById('sliderSpeed');
    const sliderField = document.getElementById('sliderField');
    const sliderArea = document.getElementById('sliderArea');
    const resetFaraday = document.getElementById('resetFaradayBtn');

    function updateFaradayReadouts() {
      state.faraday.turns = parseInt(sliderTurns.value, 10);
      state.faraday.speed = parseFloat(sliderSpeed.value);
      state.faraday.field = parseFloat(sliderField.value);
      state.faraday.area = parseFloat(sliderArea.value);

      document.getElementById('valCoilTurns').textContent = `${state.faraday.turns} turns`;
      document.getElementById('valMagnetSpeed').textContent = `${state.faraday.speed.toFixed(1)} m/s`;
      document.getElementById('valMagField').textContent = `${state.faraday.field.toFixed(1)} Tesla`;
      document.getElementById('valCoilArea').textContent = `${state.faraday.area.toFixed(2)} m²`;

      // Faraday's Law Calculations:
      // Peak Flux: Phi = B * A
      const peakFlux = state.faraday.field * state.faraday.area;
      // Effective interaction time delta: dt = length / speed (assume coil width 0.1m)
      const dt = 0.1 / Math.max(0.1, state.faraday.speed);
      const dPhiDt = peakFlux / dt;
      // EMF = N * dPhi/dt
      const emf = state.faraday.turns * dPhiDt;
      // Induced current through R=10 ohm coil:
      const resistance = 10.0;
      const current = emf / resistance;

      document.getElementById('readoutFlux').textContent = `${peakFlux.toFixed(3)} Wb`;
      document.getElementById('readoutRate').textContent = `${dPhiDt.toFixed(2)} Wb/s`;
      document.getElementById('readoutEMF').textContent = `${emf.toFixed(1)} V`;
      document.getElementById('readoutCurrent').textContent = `${current.toFixed(2)} A`;
    }

    [sliderTurns, sliderSpeed, sliderField, sliderArea].forEach((s) => {
      if (s) s.addEventListener('input', updateFaradayReadouts);
    });

    if (resetFaraday) {
      resetFaraday.addEventListener('click', () => {
        sliderTurns.value = 200;
        sliderSpeed.value = 4.0;
        sliderField.value = 0.8;
        sliderArea.value = 0.05;
        updateFaradayReadouts();
      });
    }

    // Concept stage buttons
    document.querySelectorAll('[data-fstage]').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-fstage]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        state.faraday.stage = parseInt(btn.dataset.fstage, 10);
        const expEl = document.getElementById('faradayStageExplanation');
        if (state.faraday.stage === 1) {
          expEl.innerHTML = '<strong>Stage 1 (Approaching):</strong> Magnetic flux entering the coil increases (\\(\\frac{d\\Phi}{dt} > 0\\)). By Lenz\'s Law, the coil induces an opposing North magnetic pole and counter-EMF to resist the incoming magnet.';
        } else if (state.faraday.stage === 2) {
          expEl.innerHTML = '<strong>Stage 2 (At Center):</strong> Inside the coil center, magnetic flux peaks momentarily so the instantaneous rate of change is zero (\\(\\frac{d\\Phi}{dt} = 0\\)). The induced EMF drops to 0 Volts momentarily at the turning point.';
        } else {
          expEl.innerHTML = '<strong>Stage 3 (Departing):</strong> As the magnet pulls away, magnetic flux collapses (\\(\\frac{d\\Phi}{dt} < 0\\)). The induced current reverses polarity to attract the departing pole, again conserving energy by doing mechanical work.';
        }
      });
    });

    updateFaradayReadouts();
    renderFaradaySimulation();

    // ---------------- Finance Controls ----------------
    const sliderFinP = document.getElementById('sliderFinP');
    const sliderFinR = document.getElementById('sliderFinR');
    const sliderFinT = document.getElementById('sliderFinT');
    const selectComp = document.getElementById('selectCompounding');
    const resetFin = document.getElementById('resetFinanceBtn');

    function updateFinanceReadouts() {
      state.finance.principal = parseFloat(sliderFinP.value);
      state.finance.rate = parseFloat(sliderFinR.value) / 100.0;
      state.finance.time = parseFloat(sliderFinT.value);
      const compVal = selectComp.value;

      document.getElementById('valFinP').textContent = `$${state.finance.principal.toLocaleString()}`;
      document.getElementById('valFinR').textContent = `${(state.finance.rate * 100).toFixed(1)}%`;
      document.getElementById('valFinT').textContent = `${state.finance.time} Years`;

      const P = state.finance.principal;
      const r = state.finance.rate;
      const t = state.finance.time;

      let A = 0;
      if (compVal === 'inf') {
        A = P * Math.exp(r * t);
      } else {
        const n = parseFloat(compVal);
        A = P * Math.pow(1 + r / n, n * t);
      }

      // Simple interest baseline: A_simple = P * (1 + r * t)
      const simpleA = P * (1 + r * t);
      const interest = A - P;
      const premium = A - simpleA;

      document.getElementById('readoutInitial').textContent = `$${Math.round(P).toLocaleString()}`;
      document.getElementById('readoutInterest').textContent = `$${Math.round(interest).toLocaleString()}`;
      document.getElementById('readoutFuture').textContent = `$${Math.round(A).toLocaleString()}`;
      document.getElementById('readoutPremium').textContent = `+$${Math.round(premium).toLocaleString()}`;

      renderFinanceSimulation();
    }

    [sliderFinP, sliderFinR, sliderFinT].forEach((s) => {
      if (s) s.addEventListener('input', updateFinanceReadouts);
    });
    if (selectComp) selectComp.addEventListener('change', updateFinanceReadouts);
    if (resetFin) {
      resetFin.addEventListener('click', () => {
        sliderFinP.value = 5000;
        sliderFinR.value = 8.0;
        sliderFinT.value = 10;
        selectComp.value = '12';
        updateFinanceReadouts();
      });
    }

    updateFinanceReadouts();
  }

  // Canvas animation for Faraday oscilloscope
  function renderFaradaySimulation() {
    const canvas = document.getElementById('faradayCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let tOffset = 0;

    function draw() {
      if (state.currentPage !== 'interactive-labs') return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const W = canvas.width;
      const H = canvas.height;
      const centerY = H / 2;

      // Draw grid lines
      ctx.strokeStyle = '#2E2724';
      ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 40) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, H);
        ctx.stroke();
      }
      for (let y = 0; y < H; y += 30) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(W, y);
        ctx.stroke();
      }

      // Center baseline
      ctx.strokeStyle = '#574B45';
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(W, centerY);
      ctx.stroke();

      const freq = (state.faraday.speed * 0.035);
      const ampEMF = Math.min(85, (state.faraday.turns / 600) * 80 * (state.faraday.speed / 4));
      const ampFlux = 45;

      // Draw Flux Waveform (Blue)
      ctx.strokeStyle = '#5B9BD5';
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      for (let x = 0; x < W; x++) {
        const y = centerY - ampFlux * Math.cos((x * freq) - tOffset);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Draw Induced EMF Waveform (Coral Red: E = -dPhi/dt => derivative is 90 deg out of phase)
      ctx.strokeStyle = '#E4674F';
      ctx.lineWidth = 2.8;
      ctx.beginPath();
      for (let x = 0; x < W; x++) {
        const y = centerY - ampEMF * Math.sin((x * freq) - tOffset);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      tOffset += 0.045 * (state.faraday.speed / 4);
      state.faraday.animId = requestAnimationFrame(draw);
    }

    if (state.faraday.animId) cancelAnimationFrame(state.faraday.animId);
    state.faraday.animId = requestAnimationFrame(draw);
  }

  // Canvas drawing for Finance comparison curve
  function renderFinanceSimulation() {
    const canvas = document.getElementById('financeCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const W = canvas.width;
    const H = canvas.height;
    const padX = 40;
    const padY = 25;

    const P = state.finance.principal;
    const r = state.finance.rate;
    const T = state.finance.time;

    // Max value calculation for scaling
    const maxFuture = P * Math.pow(1 + r, T);
    const maxY = maxFuture * 1.15;

    // Grid
    ctx.strokeStyle = '#2E2724';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padX, padY);
    ctx.lineTo(padX, H - padY);
    ctx.lineTo(W - padX, H - padY);
    ctx.stroke();

    // Plot Simple Interest (Dashed Grey)
    ctx.strokeStyle = '#A3968A';
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let yr = 0; yr <= T; yr++) {
      const val = P * (1 + r * yr);
      const px = padX + (yr / T) * (W - 2 * padX);
      const py = (H - padY) - (val / maxY) * (H - 2 * padY);
      if (yr === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Plot Compound Curve (Solid Peach/Coral)
    ctx.strokeStyle = '#F2B79A';
    ctx.lineWidth = 3.2;
    ctx.beginPath();
    for (let yr = 0; yr <= T; yr++) {
      const val = P * Math.pow(1 + r / 12, 12 * yr);
      const px = padX + (yr / T) * (W - 2 * padX);
      const py = (H - padY) - (val / maxY) * (H - 2 * padY);
      if (yr === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Data points & terminal label
    const termX = W - padX;
    const termVal = P * Math.pow(1 + r / 12, 12 * T);
    const termY = (H - padY) - (termVal / maxY) * (H - 2 * padY);

    ctx.fillStyle = '#E4674F';
    ctx.beginPath();
    ctx.arc(termX, termY, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#FAF6EE';
    ctx.font = 'bold 12px Manrope';
    ctx.fillText(`$${Math.round(termVal).toLocaleString()}`, termX - 60, termY - 10);
  }

  /* ==========================================================
     6. ADAPTIVE QUIZ RUNNER
     ========================================================== */
  async function initPracticePage() {
    const listContainer = document.getElementById('quizzesCardsContainer');
    const quizListView = document.getElementById('quizListView');
    const runnerView = document.getElementById('quizRunnerView');
    const resultsView = document.getElementById('quizResultsView');

    if (!listContainer) return;

    listContainer.innerHTML = '<p class="muted">Loading adaptive quizzes…</p>';

    try {
      const quizzes = await apiFetch('/api/quizzes');
      state.quizzes = quizzes;

      listContainer.innerHTML = quizzes.map((q) => `
        <article class="generic-block" style="display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="pill-badge pill-medium">${escapeHTML(q.subject)}</span>
              <span class="muted" style="font-size:12px;">Difficulty: ${escapeHTML(q.difficulty)}</span>
            </div>
            <h2 style="font-size:18px; margin-top:12px;">${escapeHTML(q.title)}</h2>
            <p class="muted" style="font-size:13px; margin-top:6px;">Topic: ${escapeHTML(q.topic_title || '')}</p>
            <p style="font-size:12px; color:var(--muted-text); margin-top:10px;">
              📝 ${q.question_count || 3} Questions · Tracks Evidence for Topic Mastery
            </p>
          </div>
          <button class="mini-btn mini-btn-primary" style="margin-top:16px;" onclick="window.FloatingApp.startQuiz('${q.id}')">
            Start Quiz →
          </button>
        </article>
      `).join('');
    } catch (err) {
      listContainer.innerHTML = `<p class="muted" style="color:var(--coral-dark);">${escapeHTML(err.message)}</p>`;
    }

    // Runner Handlers
    window.FloatingApp.startQuiz = async (quizId) => {
      try {
        const quizData = await apiFetch(`/api/quizzes/${quizId}`);
        state.activeQuiz = quizData;
        state.activeQuestionIdx = 0;
        state.quizUserAnswers = {};
        state.quizHintsUsed = 0;

        quizListView.style.display = 'none';
        resultsView.style.display = 'none';
        runnerView.style.display = 'block';

        renderQuizQuestion();
      } catch (e) {
        alert('Could not start quiz: ' + e.message);
      }
    };

    function renderQuizQuestion() {
      const q = state.activeQuiz.questions[state.activeQuestionIdx];
      const total = state.activeQuiz.questions.length;

      document.getElementById('runnerCounter').textContent = `Question ${state.activeQuestionIdx + 1} of ${total}`;
      document.getElementById('runnerDifficulty').textContent = q.difficulty || 'Medium';
      document.getElementById('runnerQuestionText').textContent = q.question_text;

      const hintBox = document.getElementById('runnerHintBox');
      hintBox.style.display = 'none';

      const optionsList = document.getElementById('runnerOptionsList');
      optionsList.innerHTML = q.options.map((opt, idx) => {
        const marker = String.fromCharCode(65 + idx);
        const isSelected = state.quizUserAnswers[q.id] === opt;
        return `
          <button type="button" class="quiz-option-btn ${isSelected ? 'selected' : ''}" data-opt="${escapeHTML(opt)}">
            <span class="quiz-opt-marker">${marker}</span>
            <span>${escapeHTML(opt)}</span>
          </button>
        `;
      }).join('');

      optionsList.querySelectorAll('.quiz-option-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          optionsList.querySelectorAll('.quiz-option-btn').forEach((b) => b.classList.remove('selected'));
          btn.classList.add('selected');
          state.quizUserAnswers[q.id] = btn.dataset.opt;
        });
      });

      const submitBtn = document.getElementById('runnerSubmitBtn');
      submitBtn.textContent = state.activeQuestionIdx === total - 1 ? 'Finish & Submit Quiz →' : 'Next Question →';
    }

    const hintBtn = document.getElementById('runnerHintBtn');
    if (hintBtn) {
      hintBtn.addEventListener('click', () => {
        const q = state.activeQuiz.questions[state.activeQuestionIdx];
        const hintBox = document.getElementById('runnerHintBox');
        hintBox.style.display = 'block';
        hintBox.innerHTML = `<strong>💡 Pedagogical Hint:</strong> ${escapeHTML(q.hint || 'Review the core formula definition on source page ' + (q.source_page || 14))}`;
        state.quizHintsUsed += 1;
      });
    }

    const submitBtn = document.getElementById('runnerSubmitBtn');
    if (submitBtn) {
      submitBtn.addEventListener('click', async () => {
        const q = state.activeQuiz.questions[state.activeQuestionIdx];
        if (!state.quizUserAnswers[q.id]) {
          alert('Please select an answer choice before proceeding.');
          return;
        }

        const total = state.activeQuiz.questions.length;
        if (state.activeQuestionIdx < total - 1) {
          state.activeQuestionIdx += 1;
          renderQuizQuestion();
        } else {
          // Submit completed quiz to backend Data Science persistence engine
          await finishQuizSubmission();
        }
      });
    }

    async function finishQuizSubmission() {
      const answersPayload = Object.keys(state.quizUserAnswers).map((qId) => ({
        question_id: qId,
        user_answer: state.quizUserAnswers[qId]
      }));

      try {
        const result = await apiFetch('/api/quizzes/submit', {
          method: 'POST',
          body: JSON.stringify({
            quiz_id: state.activeQuiz.quiz.id,
            topic_id: state.activeQuiz.quiz.topic_id,
            answers: answersPayload,
            hints_used: state.quizHintsUsed
          })
        });

        // Show Results View
        runnerView.style.display = 'none';
        resultsView.style.display = 'block';

        document.getElementById('resultsScorePct').textContent = `${result.score_pct}%`;
        document.getElementById('resultsSummaryText').textContent =
          `You answered ${result.correct_count} of ${result.total_questions} questions correctly. Evidence recorded for Data Science mastery estimation.`;

        const breakdownList = document.getElementById('resultsBreakdownList');
        breakdownList.innerHTML = result.graded_responses.map((r, i) => `
          <div class="citation-card" style="border-left:4px solid ${r.is_correct ? 'var(--sage)' : 'var(--coral)'};">
            <div style="display:flex; justify-content:space-between;">
              <span style="font-weight:700;">Question ${i + 1} — ${r.is_correct ? '✓ Correct' : '✕ Incorrect'}</span>
            </div>
            <p style="font-size:13.5px; margin-top:4px;"><strong>Your Answer:</strong> ${escapeHTML(r.user_answer)}</p>
            ${!r.is_correct ? `<p style="font-size:13.5px; color:#2F4D25;"><strong>Expected Answer:</strong> ${escapeHTML(r.correct_answer)}</p>` : ''}
            <div class="explanation-box" style="margin-top:8px;">
              <strong>Textbook Rationale:</strong> ${escapeHTML(r.explanation || 'Verified from curriculum.')}
            </div>
          </div>
        `).join('');

      } catch (err) {
        alert('Error submitting quiz: ' + err.message);
      }
    }
  }

  /* ==========================================================
     7. MY LEARNING GAPS (DATA SCIENCE)
     ========================================================== */
  async function initLearningGapsPage() {
    const container = document.getElementById('gapsContainer');
    if (!container) return;

    container.innerHTML = '<p class="muted">Analyzing assessment records for learning gaps…</p>';

    try {
      const gaps = await apiFetch('/api/gaps');
      state.gaps = gaps;

      if (!gaps || gaps.length === 0) {
        container.innerHTML = `
          <div class="generic-block wide" style="text-align:center; padding:36px;">
            <p style="font-size:18px; color:#35532A; font-weight:700;">✓ No Critical Learning Gaps Detected!</p>
            <p class="muted" style="margin-top:6px;">Your recent assessment accuracy across all evaluated topics exceeds threshold requirements.</p>
            <button class="mini-btn mini-btn-primary" style="margin-top:14px;" onclick="window.FloatingApp.goToPage('practice')">Take a New Diagnostic Quiz</button>
          </div>
        `;
        return;
      }

      container.innerHTML = gaps.map((g) => `
        <article class="gap-card">
          <div class="gap-top">
            <div>
              <span class="gap-subject">${escapeHTML(g.subject)}</span>
              <h2 class="gap-title">${escapeHTML(g.topic_title)}</h2>
            </div>
            <span class="pill-badge ${g.severity === 'High' ? 'pill-high' : 'pill-medium'}">${g.severity} Priority Gap</span>
          </div>

          <div class="gap-evidence">
            <strong>Diagnostic Evidence:</strong> ${escapeHTML(g.explanation)}
          </div>

          <p class="gap-remedy">
            <strong>Recommended Remedy:</strong> ${escapeHTML(g.suggested_remedy)}
          </p>

          <div style="display:flex; gap:12px; margin-top:8px;">
            <button class="mini-btn mini-btn-primary" onclick="window.FloatingApp.goToPage('revision')">View in Study Plan →</button>
            <button class="mini-btn" onclick="window.FloatingApp.goToPage('interactive-labs')">Open Simulation Lab</button>
            <button class="mini-btn" onclick="window.FloatingApp.goToPage('ai-teacher')">Ask Socratic AI</button>
          </div>
        </article>
      `).join('');
    } catch (err) {
      container.innerHTML = `<p class="muted" style="color:var(--coral-dark);">${escapeHTML(err.message)}</p>`;
    }
  }

  /* ==========================================================
     8. PERSONALIZED STUDY PLAN
     ========================================================== */
  async function initStudyPlanPage() {
    const container = document.getElementById('studyPlanContainer');
    const refreshBtn = document.getElementById('refreshPlanBtn');
    if (!container) return;

    async function loadPlan() {
      container.innerHTML = '<p class="muted">Generating adaptive revision schedule…</p>';
      try {
        const items = await apiFetch('/api/recommendations');
        state.studyPlan = items;

        if (!items || items.length === 0) {
          container.innerHTML = '<p class="muted">No pending study tasks. Take a quiz to generate adaptive recommendations.</p>';
          return;
        }

        container.innerHTML = items.map((item) => `
          <article class="task-item-card ${item.is_completed ? 'completed' : ''}">
            <div class="task-left">
              <input type="checkbox" class="task-checkbox" data-task-id="${item.id}" ${item.is_completed ? 'checked' : ''} />
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="pill-badge ${item.priority === 'High' ? 'pill-high' : 'pill-medium'}">${item.priority}</span>
                  <span class="task-title">${escapeHTML(item.title)}</span>
                </div>
                <p class="task-reason">${escapeHTML(item.reason)}</p>
                <p style="font-size:12px; color:var(--muted-text); margin-top:3px;">
                  ⏱ Est. ${item.duration_minutes} min · Rationale: ${escapeHTML(item.evidence)}
                </p>
              </div>
            </div>
            <div>
              <button class="mini-btn" onclick="window.FloatingApp.handleStudyItemAction('${item.action_type}')">
                ${item.action_type === 'simulation' ? 'Open Lab →' : (item.action_type === 'practice_quiz' ? 'Take Quiz →' : 'Review →')}
              </button>
            </div>
          </article>
        `).join('');

        container.querySelectorAll('.task-checkbox').forEach((box) => {
          box.addEventListener('change', async () => {
            const taskId = box.dataset.taskId;
            try {
              await apiFetch(`/api/recommendations/${taskId}/complete`, { method: 'POST' });
              box.closest('.task-item-card').classList.add('completed');
            } catch (e) {
              console.warn(e);
            }
          });
        });
      } catch (err) {
        container.innerHTML = `<p class="muted" style="color:var(--coral-dark);">${escapeHTML(err.message)}</p>`;
      }
    }

    window.FloatingApp.handleStudyItemAction = (type) => {
      if (type === 'simulation') goToPage('interactive-labs');
      else if (type === 'practice_quiz' || type === 'post_test') goToPage('practice');
      else if (type === 'worked_example') goToPage('ai-teacher');
      else goToPage('explore');
    };

    if (refreshBtn) refreshBtn.addEventListener('click', loadPlan);
    loadPlan();
  }

  /* ==========================================================
     9. LEARNING ANALYTICS & MASTERY
     ========================================================== */
  async function initAnalyticsMasteryPage() {
    const kpiAcc = document.getElementById('kpiAccuracy');
    const kpiAtt = document.getElementById('kpiAttempts');
    const kpiGaps = document.getElementById('kpiGaps');
    const masteryListEl = document.getElementById('masteryBreakdownList');
    const mistakesListEl = document.getElementById('repeatedMistakesList');

    try {
      const dashboard = await apiFetch('/api/analytics/dashboard');
      const evalData = await apiFetch('/api/evaluation');

      const eda = dashboard.eda;
      const mastery = dashboard.mastery_overview;

      if (kpiAcc) kpiAcc.textContent = eda.has_data ? `${Math.round(eda.overall_accuracy * 100)}%` : '0%';
      if (kpiAtt) kpiAtt.textContent = eda.total_completed_attempts || 0;
      if (kpiGaps) kpiGaps.textContent = dashboard.active_gaps ? dashboard.active_gaps.length : 0;

      // Evaluation box numbers
      const evalHake = document.getElementById('evalHake');
      const evalPre = document.getElementById('evalPre');
      const evalPost = document.getElementById('evalPost');
      if (evalHake) evalHake.textContent = evalData.normalized_learning_gain_hake;
      if (evalPre) evalPre.textContent = `${evalData.average_pre_test_score}%`;
      if (evalPost) evalPost.textContent = `${evalData.average_post_test_score}%`;

      // Mastery breakdown bars
      if (masteryListEl) {
        masteryListEl.innerHTML = mastery.map((m) => `
          <div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="font-weight:600;">${escapeHTML(m.topic_title)}</span>
              <span style="font-variant-numeric:tabular-nums; font-weight:700;">${m.mastery_pct}% (${escapeHTML(m.confidence_level)})</span>
            </div>
            <div class="mastery-track">
              <div class="mastery-fill" style="width:${m.mastery_pct}%; background:${m.mastery_pct >= 80 ? 'var(--sage)' : (m.mastery_pct >= 60 ? 'var(--gold)' : 'var(--coral)')};"></div>
            </div>
            <p style="font-size:12px; color:var(--muted-text); margin-top:4px;">
              ${m.total_questions} questions evaluated across ${m.attempts_count} attempt(s) · ${escapeHTML(m.suggested_next_action || '')}
            </p>
          </div>
        `).join('');
      }

      // Recurring mistake diagnosis
      if (mistakesListEl) {
        if (!eda.repeated_mistakes || eda.repeated_mistakes.length === 0) {
          mistakesListEl.innerHTML = '<p class="muted">No repeated mistake patterns detected.</p>';
        } else {
          mistakesListEl.innerHTML = eda.repeated_mistakes.map((err) => `
            <div class="citation-card" style="margin-bottom:10px; border-left:3px solid var(--coral);">
              <span class="pill-badge pill-high">${err.wrong_count} Repeated Errors</span>
              <p style="font-size:13px; font-weight:600; margin-top:4px;">${escapeHTML(err.topic_title)}</p>
              <p style="font-size:12.5px; color:var(--charcoal-light);">${escapeHTML(err.question_text)}</p>
            </div>
          `).join('');
        }
      }

      animateProgressBars();
    } catch (err) {
      console.warn('Analytics page load error:', err);
    }
  }

  /* ==========================================================
     10. MISSION-BASED LEARNING
     ========================================================== */
  async function initMissionsPage() {
    const container = document.getElementById('missionsContainer');
    if (!container) return;

    container.innerHTML = '<p class="muted">Loading mission scenarios…</p>';

    try {
      const missions = await apiFetch('/api/missions');
      state.missions = missions;

      container.innerHTML = missions.map((m) => `
        <article class="mission-card" id="mission-card-${m.id}">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
            <div>
              <span class="pill-badge pill-medium">${escapeHTML(m.subject)}</span>
              <h2 style="font-size:20px; color:var(--burgundy-dark); margin-top:4px;">${escapeHTML(m.title)}</h2>
            </div>
            <span class="pill-tag">${escapeHTML(m.topic)}</span>
          </div>

          <div class="mission-scenario">${escapeHTML(m.scenario)}</div>

          <div class="mission-form">
            <div>
              <label style="font-size:12px; font-weight:700; color:var(--muted-text);">Calculated Metric:</label>
              <input type="number" step="any" class="mission-input" id="input-metric-${m.id}" placeholder="e.g. 12514.46" />
            </div>
            <div>
              <label style="font-size:12px; font-weight:700; color:var(--muted-text);">Mathematical Justification:</label>
              <input type="text" class="mission-input" id="input-reason-${m.id}" placeholder="Explain formula step applied..." />
            </div>
            <button class="mini-btn mini-btn-primary" onclick="window.FloatingApp.submitMission('${m.id}')">Submit Solution →</button>
          </div>

          <div id="feedback-${m.id}" style="display:none;" class="mission-feedback"></div>
        </article>
      `).join('');

      window.FloatingApp.submitMission = async (missionId) => {
        const metricInput = document.getElementById(`input-metric-${missionId}`);
        const reasonInput = document.getElementById(`input-reason-${missionId}`);
        const feedbackEl = document.getElementById(`feedback-${missionId}`);

        const val = parseFloat(metricInput.value);
        if (isNaN(val)) {
          alert('Please enter a valid calculated numerical metric.');
          return;
        }

        try {
          const res = await apiFetch('/api/missions/submit', {
            method: 'POST',
            body: JSON.stringify({
              mission_id: missionId,
              calculated_metric: val,
              explanation: reasonInput.value || 'Applied standard equation'
            })
          });

          feedbackEl.style.display = 'block';
          feedbackEl.className = `mission-feedback ${res.is_passed ? 'success' : 'warning'}`;
          feedbackEl.innerHTML = `<strong>${res.is_passed ? 'Score: 100/100' : 'Score: ' + res.score + '/100'}</strong><br>${escapeHTML(res.feedback)}`;
        } catch (err) {
          alert('Submission error: ' + err.message);
        }
      };
    } catch (err) {
      container.innerHTML = `<p class="muted" style="color:var(--coral-dark);">${escapeHTML(err.message)}</p>`;
    }
  }

  /* ==========================================================
     11. SOCRATIC AI COMPANION
     ========================================================== */
  function initAITeacherPage() {
    const input = document.getElementById('teacherInput');
    const sendBtn = document.getElementById('sendBtnTeacher');
    const responseEl = document.getElementById('aiResponseTeacher');
    const modeChips = document.querySelectorAll('.page-ai-teacher .mode-chip');

    modeChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        modeChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        state.tutorMode = chip.dataset.mode;
      });
    });

    const handleTeacherSend = async () => {
      const query = (input.value || '').trim();
      if (!query) return;

      responseEl.hidden = false;
      responseEl.innerHTML = '<p class="ar-intro"><em>✦ Generating grounded textbook explanation…</em></p>';

      try {
        const result = await apiFetch('/api/tutor/chat', {
          method: 'POST',
          body: JSON.stringify({
            query: query,
            mode: state.tutorMode
          })
        });

        renderTutorResponse(result, responseEl);
      } catch (err) {
        responseEl.innerHTML = `<p class="ar-intro" style="color:var(--coral-dark);">Could not connect: ${escapeHTML(err.message)}</p>`;
      }
    };

    if (sendBtn) sendBtn.addEventListener('click', handleTeacherSend);
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleTeacherSend();
        }
      });
    }
  }

  function renderTutorResponse(result, container) {
    container.innerHTML = '';
    container.hidden = false;

    // Formatted text body
    const bodyEl = document.createElement('div');
    bodyEl.className = 'ar-intro';
    bodyEl.style.whiteSpace = 'pre-line';
    bodyEl.textContent = result.text;
    container.appendChild(bodyEl);

    // Citations
    if (result.citations && result.citations.length > 0) {
      const citeWrap = document.createElement('div');
      citeWrap.className = 'citation-container';
      citeWrap.innerHTML = '<p style="font-size:12px; font-weight:700; color:var(--muted-text); text-transform:uppercase;">Grounded Textbook Citations:</p>';

      result.citations.forEach((c) => {
        const card = document.createElement('div');
        card.className = 'citation-card';
        card.innerHTML = `
          <div class="citation-header">
            <span>📖 Page ${c.page_number} — ${escapeHTML(c.heading || 'Section')}</span>
            <span class="muted" style="font-size:11px;">${escapeHTML(c.document_title)}</span>
          </div>
          <p class="citation-excerpt">"${escapeHTML(c.excerpt)}"</p>
        `;
        citeWrap.appendChild(card);
      });
      container.appendChild(citeWrap);
    }
  }

  /* ==========================================================
     12. SETTINGS & DEMO DATA
     ========================================================== */
  function initSettingsPage() {
    const saveKeyBtn = document.getElementById('saveApiKeyBtn');
    const inputKey = document.getElementById('inputApiKey');
    const keyMsg = document.getElementById('apiKeyStatusMsg');
    const btnReset = document.getElementById('btnResetDemoData');
    const btnClear = document.getElementById('btnClearLearnerData');
    const demoMsg = document.getElementById('demoActionMsg');

    if (saveKeyBtn && inputKey) {
      saveKeyBtn.addEventListener('click', async () => {
        const key = inputKey.value.trim();
        try {
          const res = await apiFetch('/api/settings/apikey', {
            method: 'POST',
            body: JSON.stringify({ api_key: key })
          });
          keyMsg.textContent = res.has_live_gemini ? '✓ Live Gemini Activated!' : '✓ Key saved (Local Grounded Engine fallback active)';
          keyMsg.style.color = 'var(--sage)';
        } catch (e) {
          keyMsg.textContent = e.message;
          keyMsg.style.color = 'var(--coral-dark)';
        }
      });
    }

    if (btnReset) {
      btnReset.addEventListener('click', async () => {
        try {
          const res = await apiFetch('/api/demo/reset', { method: 'POST' });
          demoMsg.textContent = '✓ Reset complete: Authentic baseline dataset re-seeded with known gap in Integration.';
          demoMsg.style.color = 'var(--sage)';
        } catch (e) {
          demoMsg.textContent = e.message;
        }
      });
    }

    if (btnClear) {
      btnClear.addEventListener('click', async () => {
        try {
          const res = await apiFetch('/api/demo/clear', { method: 'POST' });
          demoMsg.textContent = '✓ Cleared: All learner records removed to test cold-start state.';
          demoMsg.style.color = 'var(--coral-dark)';
        } catch (e) {
          demoMsg.textContent = e.message;
        }
      });
    }
  }

  /* ==========================================================
     13. DOUBT SOLVING
     ========================================================== */
  function initDoubtPage() {
    const doubtInput = document.querySelector('.doubt-input');
    const doubtSendBtn = document.getElementById('doubtSendBtn');
    if (!doubtInput || !doubtSendBtn) return;

    doubtSendBtn.addEventListener('click', () => {
      const text = doubtInput.value.trim();
      if (!text) return;
      doubtInput.value = '';
      doubtInput.placeholder = 'Doubt recorded — routing to Socratic Companion…';
      setTimeout(() => goToPage('ai-teacher'), 600);
    });
  }

  /* ==========================================================
     VOICE SIMULATION
     ========================================================== */
  function startVoiceInput(voiceBtnEl, voiceStatusEl, inputEl) {
    if (voiceBtnEl.classList.contains('listening')) return;
    voiceBtnEl.classList.add('listening');

    if (voiceStatusEl) {
      voiceStatusEl.hidden = false;
      voiceStatusEl.textContent = '🎙 Listening to voice speech…';
    }

    setTimeout(() => {
      voiceBtnEl.classList.remove('listening');
      if (voiceStatusEl) voiceStatusEl.textContent = '✓ Voice captured: "Why does Faraday\'s Law have a negative sign?"';
      if (inputEl) inputEl.value = "Why does Faraday's Law have a negative sign?";
      setTimeout(() => {
        if (voiceStatusEl) voiceStatusEl.hidden = true;
      }, 2000);
    }, 1500);
  }

  function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ==========================================================
     GLOBAL NAV EVENT BINDING
     ========================================================== */
  function bindGlobalNavEvents() {
    document.querySelectorAll('.nav-item').forEach((btn) => {
      btn.addEventListener('click', () => goToPage(btn.dataset.page));
    });
    document.querySelectorAll('.bnav-item').forEach((btn) => {
      btn.addEventListener('click', () => goToPage(btn.dataset.page));
    });

    hamburgerBtn.addEventListener('click', toggleMobileSidebar);
    sidebarOverlay.addEventListener('click', closeMobileSidebar);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMobileSidebar();
    });
  }

  /* ==========================================================
     INIT
     ========================================================== */
  function init() {
    bindGlobalNavEvents();
    renderPage('home');
    setActiveNav('home');
  }

  document.addEventListener('DOMContentLoaded', init);
})();