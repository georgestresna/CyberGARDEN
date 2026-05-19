/* ================================================================
   CYBER-GARDEN — js/main.js
================================================================ */

let _data        = null;
let _activeRange = '30m'; // Modifié ici

function recalcStatuses(data) {
  Object.entries(data.seuils).forEach(([key, seuil]) => {
    if (!seuil.enabled) return;

    const capteur = data.capteurs[key];
    const value   = capteur.value;
    const hasMin  = seuil.min !== null && seuil.min !== '';
    const hasMax  = seuil.max !== null && seuil.max !== '';

    if (hasMax && value > Number(seuil.max)) {
      capteur.status    = 'alert';
      capteur.threshold = `> ${seuil.max} ${capteur.unit}`;
    } else if (hasMin && value < Number(seuil.min)) {
      capteur.status    = 'warn';
      capteur.threshold = `< ${seuil.min} ${capteur.unit}`;
    } else {
      capteur.status    = 'ok';
      capteur.threshold = (hasMin || hasMax)
        ? `${hasMin ? seuil.min : '—'} – ${hasMax ? seuil.max : '—'} ${capteur.unit}`
        : null;
    }
  });
}

function renderAll(data, range) {
  renderMetrics(data.capteurs);
  renderActionneurs(data.actionneurs, data.cuve);
  renderChart(data.historique, range);
  renderReport(data.rapport);
  renderSeuils(data.seuils, data.capteurs); // L'appel aux alertes a été supprimé
}

function initTabListeners() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn')
        .forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      _activeRange = btn.dataset.range;
      renderChart(_data.historique, _activeRange);
    });
  });
}

function onPulseClick() {
  const btn       = document.getElementById('pulse-btn');
  const label     = document.getElementById('pulse-label');
  const status    = document.getElementById('pulse-status');
  const progress  = document.getElementById('pulse-progress');
  const fill      = document.getElementById('pulse-progress-fill');

  const DURATION_MS = 5000;

  btn.disabled = true;
  btn.classList.add('active');
  label.textContent = 'Arrosage en cours…';
  status.textContent = 'Envoi de la commande…';
  progress.classList.add('visible');

  fill.style.transition = 'none';
  fill.style.width = '0%';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.transition = `width ${DURATION_MS}ms linear`;
      fill.style.width = '100%';
    });
  });

  if (typeof sendCommand === 'function') {
    sendCommand('arrosage', true)
      .then(success => {
        status.textContent = success ? '✓ Commande envoyée' : '✗ Erreur réseau';
      });
  } else {
    status.textContent = '(mode local — API non connectée)';
  }

  setTimeout(() => {
    btn.disabled = false;
    btn.classList.remove('active');
    label.textContent = 'Arroser (5 s)';
    progress.classList.remove('visible');
    fill.style.transition = 'none';
    fill.style.width = '0%';
    setTimeout(() => { status.textContent = ''; }, 3000);
  }, DURATION_MS);
}

// Nouvelle fonction de ventilation
function onVentilationClick() {
  const btn       = document.getElementById('ventilation-btn');
  const label     = document.getElementById('ventilation-label');
  const status    = document.getElementById('ventilation-status');
  const progress  = document.getElementById('ventilation-progress');
  const fill      = document.getElementById('ventilation-progress-fill');

  const DURATION_MS = 5000;

  btn.disabled = true;
  btn.classList.add('active');
  label.textContent = 'Ventilation en cours…';
  status.textContent = 'Envoi de la commande…';
  progress.classList.add('visible');

  fill.style.transition = 'none';
  fill.style.width = '0%';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.transition = `width ${DURATION_MS}ms linear`;
      fill.style.width = '100%';
    });
  });

  if (typeof sendCommand === 'function') {
    sendCommand('ventilation', true)
      .then(success => {
        status.textContent = success ? '✓ Commande envoyée' : '✗ Erreur réseau';
      });
  } else {
    status.textContent = '(mode local — API non connectée)';
  }

  setTimeout(() => {
    btn.disabled = false;
    btn.classList.remove('active');
    label.textContent = 'Ventiler (5 s)';
    progress.classList.remove('visible');
    fill.style.transition = 'none';
    fill.style.width = '0%';
    setTimeout(() => { status.textContent = ''; }, 3000);
  }, DURATION_MS);
}

function initSeuilsListener() {
  document.getElementById('seuil-apply-btn').addEventListener('click', () => {
    Object.entries(_data.seuils).forEach(([key, seuil]) => {
      if (!seuil.enabled) return;

      const minEl = document.getElementById('seuil-min-' + key);
      const maxEl = document.getElementById('seuil-max-' + key);

      seuil.min = minEl && minEl.value !== '' ? Number(minEl.value) : null;
      seuil.max = maxEl && maxEl.value !== '' ? Number(maxEl.value) : null;
    });

    recalcStatuses(_data);
    renderMetrics(_data.capteurs);

    if (typeof saveSeuilsToStorage === 'function') {
      saveSeuilsToStorage(_data.seuils);
    }

    const fb = document.getElementById('seuil-feedback');
    fb.classList.add('visible');
    setTimeout(() => fb.classList.remove('visible'), 2000);
  });
}

async function init() {
  try {
    _data = await getData();
    recalcStatuses(_data);
    renderAll(_data, _activeRange);

    initTabListeners();
    // initToggleListeners();  <--- SUPPRIMEZ OU COMMENTEZ CETTE LIGNE !
    initSeuilsListener();
  } catch (err) {
    console.error('[Cyber-Garden] Erreur de chargement des données :', err);
  }
}

document.addEventListener('DOMContentLoaded', init);