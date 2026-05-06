/* ================================================================
   CYBER-GARDEN — js/render.js
   ----------------------------------------------------------------
   Fonctions d'affichage pures.

   Règles strictes de ce fichier :
     - Ne contient AUCUNE donnée en dur
     - Ne fait AUCUN appel réseau
     - Ne gère AUCUN événement utilisateur
     - Reçoit des données en paramètre et met à jour le DOM
     - Ne doit JAMAIS être modifié pour changer les données

   Chaque fonction prend en paramètre la section de données
   dont elle a besoin, ce qui la rend facilement testable.
================================================================ */


/* ================================================================
   CONSTANTES VISUELLES
   (couleurs des graphiques et labels — ne dépendent pas des données)
================================================================ */
const CHART_COLORS = {
  temp:   { line: '#7dce5f', fill: 'rgba(125, 206, 95, 0.08)' },
  humSol: { line: '#5ba3e0', fill: 'rgba(91, 163, 224, 0.08)' },
  humAir: { line: '#e8a234', fill: 'rgba(232, 162, 52, 0.08)' },
};

const RANGE_LABELS = {
  '6h':  '6 dernières heures',
  '24h': '24 dernières heures',
  '7j':  '7 derniers jours',
};

const BADGE_LABELS = {
  ok:    'Normal',
  warn:  'Bas',
  alert: 'Alerte',
};

const ALERT_COLORS = {
  ok:    '#7dce5f',
  warn:  '#e8a234',
  alert: '#e05b5b',
};

/* Instance Chart.js — conservée en module-level pour pouvoir
   la détruire avant de recréer le graphique */
let _chartInstance = null;


/* ================================================================
   renderMetrics(capteurs)
   ----------------------------------------------------------------
   Affiche les 4 cartes de métriques (temp, hum_air, hum_sol, lux).
   @param {Object} capteurs — DATA.capteurs
================================================================ */
function renderMetrics(capteurs) {
  const grid = document.getElementById('metrics-grid');
  grid.innerHTML = '';

  Object.values(capteurs).forEach(capteur => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.style.setProperty('--card-accent', capteur.accent);

    const trendText = capteur.threshold
      ? `Seuil : ${capteur.threshold} ${capteur.unit}`
      : `Moy. 24h : ${capteur.avg24h} ${capteur.unit}`;

    card.innerHTML = `
      <div class="metric-label">${capteur.label}</div>
      <div class="metric-value-row">
        <span class="metric-value">${capteur.value}</span>
        <span class="metric-unit">${capteur.unit}</span>
      </div>
      <span class="metric-badge badge-${capteur.status}">
        ${BADGE_LABELS[capteur.status]}
      </span>
      <div class="metric-trend">${trendText}</div>
    `;
    grid.appendChild(card);
  });
}


/* ================================================================
   renderActionneurs(actionneurs, cuve)
   ----------------------------------------------------------------
   Affiche les toggles ON/OFF et la jauge cylindrique de la cuve.
   @param {Object} actionneurs — DATA.actionneurs
   @param {Object} cuve        — DATA.cuve
================================================================ */
function renderActionneurs(actionneurs, cuve) {
  /* ── Toggles (ventilation + éclairage uniquement)
        L'arrosage a son propre bouton pulse — on l'exclut ici ── */
  const list = document.getElementById('actions-list');
  list.innerHTML = '';

  Object.entries(actionneurs)
    .filter(([key]) => key !== 'arrosage')   // ← arrosage géré par le bouton pulse
    .forEach(([key, actionneur]) => {
    const row = document.createElement('div');
    row.className = 'action-row';

    const subText = actionneur.active
      ? `Mode ${actionneur.mode}`
      : `Mode ${actionneur.mode} — OFF`;

    row.innerHTML = `
      <div class="action-info">
        <div class="action-name">${actionneur.label}</div>
        <div class="action-sub" id="sub-${key}">${subText}</div>
      </div>
      <label class="toggle-wrap">
        <input type="checkbox"
               data-key="${key}"
               ${actionneur.active ? 'checked' : ''}>
        <span class="toggle-track"></span>
      </label>
    `;
    list.appendChild(row);
  });

  /* ── Cylindre cuve ───────────────────────────────────────────── */
  const { pct, litres_restants, litres_total } = cuve;

  document.getElementById('cylinder-fill').style.height = pct + '%';
  document.getElementById('water-value-label').textContent =
    `${litres_restants} L / ${litres_total} L (${pct} %)`;

  // Ticks de l'axe (100% en haut → 0% en bas)
  const axis = document.getElementById('cylinder-axis');
  axis.innerHTML = ['100%', '75%', '50%', '25%', '0%']
    .map(t => `<span class="axis-tick">${t}</span>`)
    .join('');

  // Lignes horizontales internes
  const grid = document.getElementById('cylinder-grid');
  grid.innerHTML = [0, 1, 2, 3, 4]
    .map(() => `<div class="cylinder-line"></div>`)
    .join('');
}


/* ================================================================
   renderChart(historique, range)
   ----------------------------------------------------------------
   Crée ou recrée le graphique Chart.js pour la plage donnée.
   @param {Object} historique — DATA.historique
   @param {string} range      — '6h' | '24h' | '7j'
================================================================ */
function renderChart(historique, range) {
  const points  = historique[range];
  const labels  = points.map(p => p.t);
  const temps   = points.map(p => p.temp);
  const humSols = points.map(p => p.hum_sol);
  const humAirs = points.map(p => p.hum_air);

  const ctx = document.getElementById('main-chart').getContext('2d');

  if (_chartInstance) _chartInstance.destroy();

  _chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label:           'Température (°C)',
          data:            temps,
          borderColor:     CHART_COLORS.temp.line,
          backgroundColor: CHART_COLORS.temp.fill,
          borderWidth:     2,
          pointRadius:     3,
          pointHoverRadius: 5,
          tension:         0.4,
          fill:            true,
        },
        {
          label:           'Humidité sol (%)',
          data:            humSols,
          borderColor:     CHART_COLORS.humSol.line,
          backgroundColor: CHART_COLORS.humSol.fill,
          borderWidth:     2,
          pointRadius:     3,
          pointHoverRadius: 5,
          tension:         0.4,
          fill:            true,
        },
        {
          label:           'Humidité air (%)',
          data:            humAirs,
          borderColor:     CHART_COLORS.humAir.line,
          backgroundColor: CHART_COLORS.humAir.fill,
          borderWidth:     2,
          pointRadius:     3,
          pointHoverRadius: 5,
          tension:         0.4,
          fill:            true,
        },
      ],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 400 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1c2520',
          borderColor:     'rgba(255,255,255,0.1)',
          borderWidth:     1,
          titleColor:      '#e8ede6',
          bodyColor:       '#7a9070',
          padding:         10,
          titleFont:       { family: 'DM Mono', size: 11 },
          bodyFont:        { family: 'DM Mono', size: 11 },
        },
      },
      scales: {
        x: {
          ticks:  { color: '#445540', font: { family: 'DM Mono', size: 10 } },
          grid:   { color: 'rgba(255,255,255,0.04)' },
          border: { color: 'rgba(255,255,255,0.06)' },
        },
        y: {
          ticks:  { color: '#445540', font: { family: 'DM Mono', size: 10 } },
          grid:   { color: 'rgba(255,255,255,0.04)' },
          border: { color: 'rgba(255,255,255,0.06)' },
        },
      },
    },
  });

  document.getElementById('chart-range-label').textContent = RANGE_LABELS[range];
}


/* ================================================================
   renderReport(rapport)
   ----------------------------------------------------------------
   Affiche le tableau du rapport journalier.
   @param {Object} rapport — DATA.rapport
================================================================ */
function renderReport(rapport) {
  document.getElementById('report-date-label').textContent = rapport.date;

  const rows = [
    ['Température moy.',  rapport.temp_moy],
    ['Humidité air moy.', rapport.hum_air_moy],
    ['Humidité sol moy.', rapport.hum_sol_moy],
    ['Arrosages',         rapport.arrosages],
    ['Luminosité moy.',   rapport.luminosite_moy],
    ['Eau consommée',     rapport.consommation],
  ];

  document.getElementById('report-table').innerHTML = rows
    .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`)
    .join('');
}


/* ================================================================
   renderAlerts(alertes)
   ----------------------------------------------------------------
   Affiche la liste des alertes récentes.
   @param {Array} alertes — DATA.alertes
================================================================ */
function renderAlerts(alertes) {
  document.getElementById('alert-list').innerHTML = alertes
    .map(a => `
      <div class="alert-item">
        <div class="alert-indicator"
             style="background:${ALERT_COLORS[a.type]}"></div>
        <span class="alert-text">${a.message}</span>
        <span class="alert-time">${a.heure}</span>
      </div>
    `)
    .join('');
}


/* ================================================================
   renderSeuils(seuils, capteurs)
   ----------------------------------------------------------------
   Affiche le panneau de configuration des seuils.
   @param {Object} seuils   — DATA.seuils
   @param {Object} capteurs — DATA.capteurs (pour labels et unités)
================================================================ */
function renderSeuils(seuils, capteurs) {
  const grid = document.getElementById('seuils-grid');
  grid.innerHTML = '';

  Object.entries(seuils).forEach(([key, seuil]) => {
    const capteur = capteurs[key];
    const block   = document.createElement('div');
    block.className = 'seuil-block' + (seuil.enabled ? '' : ' disabled');
    block.style.setProperty('--seuil-accent', capteur.accent);

    if (seuil.enabled) {
      block.innerHTML = `
        <div class="seuil-capteur-label">${capteur.label}</div>
        <div class="seuil-row">
          <span class="seuil-row-label">Min ↓</span>
          <div class="seuil-input-wrap">
            <input class="seuil-input" type="number"
                   id="seuil-min-${key}"
                   value="${seuil.min ?? ''}"
                   placeholder="—">
            <span class="seuil-unit">${capteur.unit}</span>
          </div>
        </div>
        <div class="seuil-row">
          <span class="seuil-row-label">Max ↑</span>
          <div class="seuil-input-wrap">
            <input class="seuil-input" type="number"
                   id="seuil-max-${key}"
                   value="${seuil.max ?? ''}"
                   placeholder="—">
            <span class="seuil-unit">${capteur.unit}</span>
          </div>
        </div>
      `;
    } else {
      block.innerHTML = `
        <div class="seuil-capteur-label">${capteur.label}</div>
        <div class="seuil-na">Pas de seuil configuré</div>
      `;
    }

    grid.appendChild(block);
  });
}