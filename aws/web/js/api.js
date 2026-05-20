/* ================================================================
   CYBER-GARDEN — js/api.js
================================================================ */

const API_BASE_URL = 'http://13.63.71.56:8000';

// const ROUTES = {
//   latest:      `${API_BASE_URL}/api/latest`,
//   history30m:  `${API_BASE_URL}/api/history?range=30m`,
//   report1h:    `${API_BASE_URL}/api/report/1h`,
//   pulse:       `${API_BASE_URL}/api/command/pulse`,
//   ventilation: `${API_BASE_URL}/api/command/ventilation` // Nouveau
// };

const ROUTES = {
  latest: `${API_BASE_URL}/api/latest`,
  history30m: `${API_BASE_URL}/api/history?range=30m`,
  history6h: `${API_BASE_URL}/api/history?range=6h`,
  history24h: `${API_BASE_URL}/api/history?range=24h`,
  history7j: `${API_BASE_URL}/api/history?range=7j`,
  report: `${API_BASE_URL}/api/report/today`,
  report1h: `${API_BASE_URL}/api/report/1h`,
  alerts: `${API_BASE_URL}/api/alerts?limit=10`,

  // --- UPDATED COMMAND ROUTES ---
  arrosage: `${API_BASE_URL}/api/command/water`,
  ventilation: `${API_BASE_URL}/api/command/fan`
};

const FETCH_TIMEOUT_MS = 5000;
const CUVE_DISTANCE_VIDE_CM   = 30;
const CUVE_DISTANCE_PLEINE_CM = 3;
const CUVE_LITRES_TOTAL       = 5.0;

const _FALLBACK_DATA = {
  capteurs: {
    temperature:  { label: 'Température',  value: null, unit: '°C',  avg1h: null, status: 'ok', threshold: null, accent: '#7dce5f' },
    humidite_air: { label: 'Humidité air', value: null, unit: '%',   avg1h: null, status: 'ok', threshold: null, accent: '#5ba3e0' },
    humidite_sol: { label: 'Humidité sol', value: null, unit: '%',   avg1h: null, status: 'ok', threshold: null, accent: '#e8a234' },
    luminosite:   { label: 'Luminosité',   value: null, unit: 'lux', avg1h: null, status: 'ok', threshold: null, accent: '#a78be0' },
  },
  actionneurs: {
    arrosage:    { label: 'Arrosage',    active: false, mode: 'auto'   },
    ventilation: { label: 'Ventilation', active: false, mode: 'auto'   },
  },
  cuve: { pct: 0, litres_restants: 0, litres_total: CUVE_LITRES_TOTAL },
  historique: { '30m': [] },
  rapport: {
    date: '—', temp_moy: '—', hum_air_moy: '—', hum_sol_moy: '—',
    arrosages: '—', luminosite_moy: '—', consommation: '—',
  },
  seuils: null,
};

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

function formatTimestamp(ts, range) {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function distanceToPct(distanceCm) {
  if (distanceCm == null) return 0;
  const range = CUVE_DISTANCE_VIDE_CM - CUVE_DISTANCE_PLEINE_CM;
  const fill  = CUVE_DISTANCE_VIDE_CM - distanceCm;
  const pct   = Math.round((fill / range) * 100);
  return Math.max(0, Math.min(100, pct));
}

function adaptLatest(doc) {
  const pct = distanceToPct(doc.distance);
  return {
    capteurs: {
      temperature: { label: 'Température', unit: '°C', accent: '#7dce5f', value: doc.temperature ?? null, avg1h: null, status: 'ok', threshold: null },
      humidite_air: { label: 'Humidité air', unit: '%', accent: '#5ba3e0', value: doc.humidite ?? null, avg1h: null, status: 'ok', threshold: null },
      humidite_sol: { label: 'Humidité sol', unit: '%', accent: '#e8a234', value: doc.humidite_sol ?? null, avg1h: null, status: 'ok', threshold: null },
      luminosite: { label: 'Luminosité', unit: 'lux', accent: '#a78be0', value: doc.lumiere ?? null, avg1h: null, status: 'ok', threshold: null },
    },
    actionneurs: {
      arrosage:    { label: 'Arrosage',    active: false, mode: 'auto' },
      ventilation: { label: 'Ventilation', active: false, mode: 'auto' },
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
    hum_sol: doc.humidite_sol ?? 0,
    hum_air: doc.humidite    ?? 0,
  }));
}

function adaptReport(doc) {
  return {
    date: doc.date || "Dernière Heure",
    temp_moy: doc.temp_moyenne != null ? `${doc.temp_moyenne} °C` : '—',
    hum_air_moy: doc.humidite_air_moyenne != null ? `${doc.humidite_air_moyenne} %` : '—',

    // CHANGED: This now reads the soil moisture from your Python backend!
    hum_sol_moy: doc.humidite_sol_moyenne != null ? `${doc.humidite_sol_moyenne}` : '—',

    arrosages: doc.nb_arrosages != null ? `${doc.nb_arrosages} déclenchement(s)` : '—',
    luminosite_moy: doc.luminosite_moyenne != null ? `${doc.luminosite_moyenne} lux` : '—',
    consommation: doc.volume_eau_l != null ? `${doc.volume_eau_l} L` : '—',
  };
}

async function sendCommand(actionneur, etat) {
  const route = actionneur === 'ventilation' ? ROUTES.ventilation : ROUTES.arrosage;

  try {
    const res = await fetchWithTimeout(route, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ state: etat ? 1 : 0 })
    });
    const json = await res.json();
    console.log(`[Cyber-Garden] Commande ${actionneur} (${etat ? 'ON' : 'OFF'}) envoyée :`, json);
    return json.status === 'success';
  } catch (err) {
    console.warn(`[Cyber-Garden] Échec commande ${actionneur} :`, err.message);
    return false;
  }
}

async function getData() {
  const seuils = _loadSeuilsFromStorage();
  try {
    const [latestRes, h30mRes, reportRes] = await Promise.all([
      fetchWithTimeout(ROUTES.latest),
      fetchWithTimeout(ROUTES.history30m),
      fetchWithTimeout(ROUTES.report1h),
    ]);

    const [latestDoc, h30m, reportDoc] = await Promise.all([
      latestRes.json(),
      h30mRes.json(),
      reportRes.json(),
    ]);

    const { capteurs, actionneurs, cuve } = adaptLatest(latestDoc);

    return {
      capteurs,
      actionneurs,
      cuve,
      historique: {
        '30m': adaptHistory(h30m, '30m'),
      },
      rapport: adaptReport(reportDoc),
      seuils,
    };
  } catch (err) {
    console.warn('[Cyber-Garden] API inaccessible — fallback activé :', err.message);
    return {
      ..._FALLBACK_DATA,
      seuils,
    };
  }
}

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