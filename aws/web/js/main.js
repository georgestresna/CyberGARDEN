/* ================================================================
   CYBER-GARDEN — js/main.js
   ----------------------------------------------------------------
   Point d'entrée de l'application.

   Responsabilités de ce fichier :
     1. Charger les données via getData() (défini dans api.js)
     2. Appliquer la logique métier (recalcul des statuts)
     3. Appeler les fonctions de rendu (définies dans render.js)
     4. Attacher les écouteurs d'événements

   Ce fichier ne contient pas de données en dur et ne fait
   pas de manipulation DOM directe (délégué à render.js).
================================================================ */


/* ================================================================
   1. ÉTAT LOCAL
   ----------------------------------------------------------------
   On garde une référence aux données chargées pour pouvoir les
   relire lors des interactions (ex: changement de plage de graphique,
   modification des seuils).
================================================================ */
let _data        = null;   // données complètes renvoyées par getData()
let _activeRange = '6h';  // onglet actif du graphique


/* ================================================================
   2. LOGIQUE MÉTIER — recalcul des statuts
   ----------------------------------------------------------------
   Lit DATA.seuils et met à jour DATA.capteurs[x].status
   en conséquence. Appelé à l'init et à chaque "Appliquer".
================================================================ */
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


/* ================================================================
   3. RENDU COMPLET
   ----------------------------------------------------------------
   Appelle toutes les fonctions de render.js dans l'ordre.
   Appelé une fois à l'init (après chargement des données).
================================================================ */
function renderAll(data, range) {
  renderMetrics(data.capteurs);
  renderActionneurs(data.actionneurs, data.cuve);
  renderChart(data.historique, range);
  renderReport(data.rapport);
  renderAlerts(data.alertes);
  renderSeuils(data.seuils, data.capteurs);
}


/* ================================================================
   4. GESTIONNAIRES D'ÉVÉNEMENTS
================================================================ */

/* ── Onglets graphique (6h / 24h / 7j) ──────────────────────── */
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

/* ── Toggles actionneurs ─────────────────────────────────────── */
function initToggleListeners() {
  // Délégation : écoute sur le conteneur parent plutôt que
  // sur chaque toggle (les toggles sont générés dynamiquement)
  document.getElementById('actions-list').addEventListener('change', e => {
    const input = e.target;
    if (!input.dataset.key) return;

    const key    = input.dataset.key;
    const isOn   = input.checked;
    const subEl  = document.getElementById('sub-' + key);

    // Mise à jour de l'état local
    _data.actionneurs[key].active = isOn;

    // Mise à jour du sous-titre
    if (subEl) {
      subEl.textContent = isOn
        ? `Mode ${_data.actionneurs[key].mode}`
        : `Mode ${_data.actionneurs[key].mode} — OFF`;
    }

    /* Envoie la commande à l'API si api.js est chargé */
    if (typeof sendCommand === 'function') {
      sendCommand(key, isOn);
    }
  });
}

/* ── Bouton arrosage impulsion (5 secondes) ──────────────────── */
function onPulseClick() {
  const btn       = document.getElementById('pulse-btn');
  const label     = document.getElementById('pulse-label');
  const status    = document.getElementById('pulse-status');
  const progress  = document.getElementById('pulse-progress');
  const fill      = document.getElementById('pulse-progress-fill');

  const DURATION_MS = 5000;

  /* Verrouiller le bouton pendant l'arrosage */
  btn.disabled = true;
  btn.classList.add('active');
  label.textContent = 'Arrosage en cours…';
  status.textContent = 'Envoi de la commande…';
  progress.classList.add('visible');

  /* Barre de progression sur 5 secondes */
  fill.style.transition = 'none';
  fill.style.width = '0%';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.transition = `width ${DURATION_MS}ms linear`;
      fill.style.width = '100%';
    });
  });

  /* Appel API — POST /api/command/pulse */
  if (typeof sendCommand === 'function') {
    sendCommand('arrosage', true)
      .then(success => {
        status.textContent = success ? '✓ Commande envoyée' : '✗ Erreur réseau';
      });
  } else {
    status.textContent = '(mode local — API non connectée)';
  }

  /* Réactiver après 5 secondes */
  setTimeout(() => {
    btn.disabled = false;
    btn.classList.remove('active');
    label.textContent = 'Arroser (5 s)';
    progress.classList.remove('visible');
    fill.style.transition = 'none';
    fill.style.width = '0%';
    /* Effacer le statut après 3s supplémentaires */
    setTimeout(() => { status.textContent = ''; }, 3000);
  }, DURATION_MS);
}


/* ── Bouton "Appliquer les seuils" ───────────────────────────── */
function initSeuilsListener() {
  document.getElementById('seuil-apply-btn').addEventListener('click', () => {

    // 1. Lire les valeurs saisies dans les inputs
    Object.entries(_data.seuils).forEach(([key, seuil]) => {
      if (!seuil.enabled) return;

      const minEl = document.getElementById('seuil-min-' + key);
      const maxEl = document.getElementById('seuil-max-' + key);

      seuil.min = minEl && minEl.value !== '' ? Number(minEl.value) : null;
      seuil.max = maxEl && maxEl.value !== '' ? Number(maxEl.value) : null;
    });

    // 2. Recalculer les statuts
    recalcStatuses(_data);

    // 3. Redessiner uniquement les cartes métriques
    renderMetrics(_data.capteurs);

    // 4. Sauvegarder les seuils en localStorage (si api.js est chargé)
    if (typeof saveSeuilsToStorage === 'function') {
      saveSeuilsToStorage(_data.seuils);
    }

    // 5. Feedback visuel (2 secondes)
    const fb = document.getElementById('seuil-feedback');
    fb.classList.add('visible');
    setTimeout(() => fb.classList.remove('visible'), 2000);
  });
}


/* ================================================================
   5. INITIALISATION
   ----------------------------------------------------------------
   Point d'entrée principal — appelé au chargement de la page.
================================================================ */
async function init() {
  try {
    // Charger les données (mockées pour l'instant, API à l'étape 4)
    _data = await getData();

    // Appliquer la logique métier avant le premier rendu
    recalcStatuses(_data);

    // Afficher tout
    renderAll(_data, _activeRange);

    // Attacher les écouteurs
    initTabListeners();
    initToggleListeners();
    initSeuilsListener();

  } catch (err) {
    // À l'étape 4 : afficher un message d'erreur si l'API ne répond pas
    console.error('[Cyber-Garden] Erreur de chargement des données :', err);
  }
}

// Lancer l'application une fois le DOM prêt
document.addEventListener('DOMContentLoaded', init);