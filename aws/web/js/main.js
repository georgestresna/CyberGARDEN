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
    initToggleListeners();
    initSeuilsListener();
  } catch (err) {
    console.error('[Cyber-Garden] Erreur de chargement des données :', err);
  }
}

document.addEventListener('DOMContentLoaded', init);