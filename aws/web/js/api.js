/* ================================================================
   CYBER-GARDEN — js/api.js
   ----------------------------------------------------------------
   Source de données réelle — instance AWS 13.63.71.56
   Base MongoDB : cybergarden
   Collections  : sensors, commands

   Format réel d'un document "sensors" (confirmé par db.sensors.findOne()) :
   {
     _id:         ObjectId,
     temperature: 25,
     humidite:    33,       ← humidité AIR
     lumiere:     7,        ← luminosité
     distance:    7,        ← distance ultrasons HC-SR04 (niveau cuve en cm)
     timestamp:   "2026-05-05T14:51:22.463199"
   }

   Pour activer ce fichier :
   Dans index.html, remplacer <script src="js/data.js"></script>
   par                         <script src="js/api.js"></script>
================================================================ */


/* ================================================================
   1. CONFIGURATION
================================================================ */

const API_BASE_URL = 'http://13.63.71.56:8000';

const ROUTES = {
  latest:    `${API_BASE_URL}/api/latest`,
  history6h: `${API_BASE_URL}/api/history?range=6h`,
  history24h:`${API_BASE_URL}/api/history?range=24h`,
  history7j: `${API_BASE_URL}/api/history?range=7j`,
  report:    `${API_BASE_URL}/api/report/today`,
  alerts:    `${API_BASE_URL}/api/alerts?limit=10`,
  pulse:     `${API_BASE_URL}/api/command/pulse`,   // POST → impulsion 5s (pas de body)
  pump:      `${API_BASE_URL}/api/command/pump`,    // POST → ON/OFF avec { state: 1|0 }
};

const FETCH_TIMEOUT_MS = 5000;

/* Calibration du capteur de niveau (HC-SR04)
   Le capteur mesure la distance entre lui (en haut de la cuve) et la surface de l'eau.
   Distance grande = peu d'eau. Distance petite = cuve pleine.
   ⚠ À ajuster selon la hauteur réelle de votre cuve. */
const CUVE_DISTANCE_VIDE_CM   = 30;   // distance mesurée quand la cuve est vide
const CUVE_DISTANCE_PLEINE_CM = 3;    // distance mesurée quand la cuve est pleine
const CUVE_LITRES_TOTAL       = 5.0;  // capacité totale en litres


/* ================================================================
   2. DONNÉES DE FALLBACK
   Affichées si l'API ne répond pas — dashboard jamais vide.
================================================================ */
const _FALLBACK_DATA = {
  capteurs: {
    temperature:  { label: 'Température',  value: null, unit: '°C',  avg24h: null, status: 'ok', threshold: null, accent: '#7dce5f' },
    humidite_air: { label: 'Humidité air', value: null, unit: '%',   avg24h: null, status: 'ok', threshold: null, accent: '#5ba3e0' },
    humidite_sol: { label: 'Humidité sol', value: null, unit: '%',   avg24h: null, status: 'ok', threshold: null, accent: '#e8a234' },
    luminosite:   { label: 'Luminosité',   value: null, unit: 'lux', avg24h: null, status: 'ok', threshold: null, accent: '#a78be0' },
  },
  actionneurs: {
    arrosage:    { label: 'Arrosage',    active: false, mode: 'auto'   },
    ventilation: { label: 'Ventilation', active: false, mode: 'auto'   },
    eclairage:   { label: 'Éclairage',   active: false, mode: 'manuel' },
  },
  cuve: { pct: 0, litres_restants: 0, litres_total: CUVE_LITRES_TOTAL },
  historique: { '6h': [], '24h': [], '7j': [] },
  rapport: {
    date: '—', temp_moy: '—', hum_air_moy: '—', hum_sol_moy: '—',
    arrosages: '—', luminosite_moy: '—', consommation: '—',
  },
  alertes: [],
  seuils: null, // sera remplacé par _loadSeuilsFromStorage() dans getData()
};


/* ================================================================
   3. UTILITAIRES
================================================================ */

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status} sur ${url}`);
    return res;
  } finally {
    clearTimeout(timer);
  }
}

/* Formate un timestamp ISO en label court pour l'axe X du graphique */
function formatTimestamp(ts, range) {
  if (!ts) return '—';
  const d = new Date(ts);
  if (range === '7j') {
    return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric' });
  }
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

/* Convertit la distance HC-SR04 (cm) en pourcentage de remplissage.
   Plus la distance est petite, plus la cuve est pleine. */
function distanceToPct(distanceCm) {
  if (distanceCm == null) return 0;
  const range = CUVE_DISTANCE_VIDE_CM - CUVE_DISTANCE_PLEINE_CM;
  const fill  = CUVE_DISTANCE_VIDE_CM - distanceCm;
  const pct   = Math.round((fill / range) * 100);
  return Math.max(0, Math.min(100, pct));
}


/* ================================================================
   4. ADAPTATEURS
   ----------------------------------------------------------------
   Traduisent les documents MongoDB bruts vers la structure
   attendue par render.js.

   Correspondance champs MongoDB → dashboard :
     temperature → capteurs.temperature.value
     humidite    → capteurs.humidite_air.value
     lumiere     → capteurs.luminosite.value
     distance    → cuve.pct  (via distanceToPct())
     humidite_sol → null (pas de capteur sol dans le JSON de Pierre)
================================================================ */

function adaptLatest(doc) {
  const pct = distanceToPct(doc.distance);

  return {
    capteurs: {
      temperature: {
        label: 'Température', unit: '°C', accent: '#7dce5f',
        value:     doc.temperature ?? null,
        avg24h:    null,
        status:    'ok',   // recalculé par recalcStatuses() dans main.js
        threshold: null,
      },
      humidite_air: {
        label: 'Humidité air', unit: '%', accent: '#5ba3e0',
        value:     doc.humidite ?? null,   // champ MongoDB : "humidite"
        avg24h:    null,
        status:    'ok',
        threshold: null,
      },
      humidite_sol: {
        label: 'Humidité sol', unit: '%', accent: '#e8a234',
        value:     null,   // pas encore de capteur sol dans le JSON de Pierre
        avg24h:    null,
        status:    'ok',
        threshold: null,
      },
      luminosite: {
        label: 'Luminosité', unit: 'lux', accent: '#a78be0',
        value:     doc.lumiere ?? null,    // champ MongoDB : "lumiere"
        avg24h:    null,
        status:    'ok',
        threshold: null,
      },
    },
    actionneurs: {
      /* Les états des actionneurs ne sont pas stockés dans sensors.
         Initialisés à false, mis à jour localement via les toggles. */
      arrosage:    { label: 'Arrosage',    active: false, mode: 'auto'   },
      ventilation: { label: 'Ventilation', active: false, mode: 'auto'   },
      eclairage:   { label: 'Éclairage',   active: false, mode: 'manuel' },
    },
    cuve: {
      pct,
      litres_restants: parseFloat(((pct / 100) * CUVE_LITRES_TOTAL).toFixed(1)),
      litres_total:    CUVE_LITRES_TOTAL,
    },
  };
}

function adaptHistory(docs, range) {
  return docs.map(doc => ({
    t:       formatTimestamp(doc.timestamp, range),
    temp:    doc.temperature ?? 0,
    hum_sol: 0,                     // pas de capteur sol
    hum_air: doc.humidite    ?? 0,  // champ MongoDB : "humidite"
  }));
}

function adaptReport(doc) {
  const dateStr = doc.date
    ? new Date(doc.date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';

  return {
    date:           dateStr,
    temp_moy:       doc.temp_moyenne         != null ? `${doc.temp_moyenne} °C`        : '—',
    hum_air_moy:    doc.humidite_air_moyenne != null ? `${doc.humidite_air_moyenne} %` : '—',
    hum_sol_moy:    '— (pas de capteur sol)',
    arrosages:      doc.nb_arrosages         != null ? `${doc.nb_arrosages} déclenchement(s)` : '—',
    luminosite_moy: doc.luminosite_moyenne   != null ? `${doc.luminosite_moyenne} lux` : '—',
    consommation:   doc.volume_eau_l         != null ? `${doc.volume_eau_l} L`          : '—',
  };
}

function adaptAlerts(docs) {
  /* La collection "commands" contient les actions envoyées.
     On les mappe comme alertes dans le dashboard. */
  return docs.map(doc => ({
    type:    doc.status === 'sent' ? 'ok' : 'warn',
    message: `Pompe — ${doc.action ?? 'commande'} (${doc.device ?? '—'})`,
    heure:   doc.timestamp
               ? new Date(doc.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
               : '—',
  }));
}


/* ================================================================
   5. ENVOI DE COMMANDES
   ----------------------------------------------------------------
   Deux routes disponibles côté FastAPI :
     POST /api/command/pulse  → impulsion 5s, pas de body
     POST /api/command/pump   → ON/OFF avec body { state: 1|0 }

   Le bouton du dashboard utilise toujours /pulse (impulsion).
   /pump est disponible si on veut un contrôle ON/OFF manuel plus tard.
================================================================ */
async function sendCommand(actionneur, etat) {
  if (actionneur !== 'arrosage') {
    /* Ventilation et éclairage : pas encore de route API */
    console.info(`[Cyber-Garden] Commande locale : ${actionneur} = ${etat}`);
    return true;
  }

  if (!etat) {
    /* Le bouton pulse ne génère pas de commande "arrêt" —
       la pompe s'arrête automatiquement après 5s côté STM32 */
    console.info('[Cyber-Garden] Arrosage OFF — arrêt automatique après 5s.');
    return true;
  }

  try {
    /* Utilise /api/command/pulse — pas de body requis */
    const res  = await fetchWithTimeout(ROUTES.pulse, { method: 'POST' });
    const json = await res.json();
    console.log('[Cyber-Garden] Pulse envoyé :', json);
    return json.status === 'success';
  } catch (err) {
    console.warn('[Cyber-Garden] Échec commande arrosage :', err.message);
    return false;
  }
}


/* ================================================================
   6. INTERFACE PUBLIQUE — getData()
   Même signature que data.js : async function getData() → Promise
================================================================ */
async function getData() {
  const seuils = _loadSeuilsFromStorage();

  try {
    const [latestRes, h6hRes, h24hRes, h7jRes, reportRes, alertsRes] =
      await Promise.all([
        fetchWithTimeout(ROUTES.latest),
        fetchWithTimeout(ROUTES.history6h),
        fetchWithTimeout(ROUTES.history24h),
        fetchWithTimeout(ROUTES.history7j),
        fetchWithTimeout(ROUTES.report),
        fetchWithTimeout(ROUTES.alerts),
      ]);

    const [latestDoc, h6h, h24h, h7j, reportDoc, alertsDocs] =
      await Promise.all([
        latestRes.json(),
        h6hRes.json(),
        h24hRes.json(),
        h7jRes.json(),
        reportRes.json(),
        alertsRes.json(),
      ]);

    const { capteurs, actionneurs, cuve } = adaptLatest(latestDoc);

    return {
      capteurs,
      actionneurs,
      cuve,
      historique: {
        '6h':  adaptHistory(h6h,  '6h'),
        '24h': adaptHistory(h24h, '24h'),
        '7j':  adaptHistory(h7j,  '7j'),
      },
      rapport: adaptReport(reportDoc),
      alertes: adaptAlerts(alertsDocs),
      seuils,
    };

  } catch (err) {
    console.warn('[Cyber-Garden] API inaccessible — fallback activé :', err.message);
    return {
      ..._FALLBACK_DATA,
      seuils,
      alertes: [{
        type:    'alert',
        message: `API inaccessible — ${err.message}`,
        heure:   new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
      }],
    };
  }
}


/* ================================================================
   7. PERSISTANCE DES SEUILS (localStorage)
================================================================ */
const SEUILS_KEY = 'cyber_garden_seuils';

function _loadSeuilsFromStorage() {
  try {
    const raw = localStorage.getItem(SEUILS_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return {
    temperature:  { min: 15,   max: 30,   enabled: true  },
    humidite_air: { min: 40,   max: 80,   enabled: true  },
    humidite_sol: { min: 35,   max: 80,   enabled: true  },
    luminosite:   { min: null, max: null, enabled: false },
  };
}

function saveSeuilsToStorage(seuils) {
  try { localStorage.setItem(SEUILS_KEY, JSON.stringify(seuils)); } catch (_) {}
}