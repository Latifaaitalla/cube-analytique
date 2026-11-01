/**
 * Dashboard Cube Analytique Ventes
 * Données simulées représentant les résultats des requêtes Trino
 * (dans un environnement réel, remplacer par des appels API vers Trino)
 */

// ── Données simulées (sorties Trino) ─────────────────────────
const DATA = {
  // cube_mensuel_categorie agrégé par mois
  caMensuel: {
    labels: ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"],
    "2023": [312000, 258000, 285000, 302000, 318000, 345000, 392000, 378000, 295000, 308000, 352000, 520000],
    "2024": [368000, 304000, 335000, 358000, 375000, 408000, 465000, 449000, 348000, 362000, 418000, 620000],
  },

  // cube_mensuel_categorie agrégé par catégorie
  categories: {
    labels: ["Électronique","Vêtements","Sport & Loisirs","Maison & Déco","Alimentation"],
    ca:     [1_285_000, 892_000, 648_000, 524_000, 312_000],
    marge:  [38.2, 44.5, 36.8, 41.2, 28.9],
  },

  // cube_mensuel_canal
  canaux: {
    labels: ["Magasin", "En ligne", "Application", "Téléphone"],
    ca:     [1_820_000, 1_260_000, 480_000, 101_000],
    colors: ["#818cf8","#38bdf8","#34d399","#fb923c"],
  },

  // cube_mensuel_region
  regions: {
    labels: ["Île-de-France","Auvergne-RA","Provence-PACA","Occitanie","Nouvelle-Aqt","Grand Est","Hauts-de-Fr.","Bretagne"],
    ca:     [1_050_000, 720_000, 610_000, 490_000, 420_000, 355_000, 298_000, 218_000],
  },

  // requête segments clients
  segments: {
    labels: ["Premium","Entreprise","Standard","Jeune","Budget"],
    ltv:    [1_240, 980, 620, 485, 310],
    colors: ["#818cf8","#38bdf8","#34d399","#fb923c","#f87171"],
  },

  // cube_produit_top WHERE rang_ca <= 10
  topProduits: [
    { rang:1, nom:"Laptop v1",         cat:"Électronique",  ca:185_240, vol:187, marge:62_450, taux:33.7 },
    { rang:2, nom:"Smartphone v3",     cat:"Électronique",  ca:172_810, vol:248, marge:55_290, taux:32.0 },
    { rang:3, nom:"Vélo v2",           cat:"Sport & Loisirs",ca:148_500, vol:330, marge:47_520, taux:32.0 },
    { rang:4, nom:"Tablette v1",       cat:"Électronique",  ca:134_200, vol:299, marge:40_260, taux:30.0 },
    { rang:5, nom:"Montre connectée v2",cat:"Électronique", ca:118_650, vol:397, marge:38_100, taux:32.1 },
    { rang:6, nom:"Laptop v2",         cat:"Électronique",  ca:112_080, vol:113, marge:35_860, taux:32.0 },
    { rang:7, nom:"Veste v1",          cat:"Vêtements",     ca:98_400,  vol:820, marge:43_300, taux:44.0 },
    { rang:8, nom:"Casque audio v3",   cat:"Électronique",  ca:94_750,  vol:477, marge:28_425, taux:30.0 },
    { rang:9, nom:"Haltères v2",       cat:"Sport & Loisirs",ca:86_200, vol:1437,marge:28_450, taux:33.0 },
    { rang:10,nom:"Tapis yoga v1",     cat:"Sport & Loisirs",ca:79_800, vol:2280,marge:26_340, taux:33.0 },
  ],

  // KPIs annuels (requête compute_kpis)
  kpis: {
    "2023": { ca: 3_865_000, panier: 92.4, marge: 30.1, transactions: 41_830 },
    "2024": { ca: 4_579_000, panier: 97.2, marge: 31.9, transactions: 47_110 },
    "all":  { ca: 8_444_000, panier: 94.8, marge: 31.0, transactions: 88_940 },
  }
};

// ── Utilitaires formatage ─────────────────────────────────────
const fmt = {
  euro:    v => new Intl.NumberFormat('fr-FR', {style:'currency', currency:'EUR', maximumFractionDigits:0}).format(v),
  num:     v => new Intl.NumberFormat('fr-FR').format(v),
  pct:     v => `${v.toFixed(1)}%`,
};

// ── Config Chart.js globale ───────────────────────────────────
Chart.defaults.color          = '#94a3b8';
Chart.defaults.font.family    = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size      = 11;
Chart.defaults.plugins.legend.display = false;
Chart.defaults.animation.duration = 700;

const GRID_COLOR = 'rgba(148,163,184,0.08)';
const PURPLE     = '#818cf8';
const PURPLE2    = '#a78bfa';
const BLUE       = '#38bdf8';

let charts = {};

// ── Graphique 1 : CA Mensuel ─────────────────────────────────
function buildCaMensuel(annee) {
  const ctx = document.getElementById('chart-ca-mensuel');
  if (!ctx) return;

  const show2023 = annee === 'all' || annee === '2023';
  const show2024 = annee === 'all' || annee === '2024';

  const datasets = [];
  if (show2023) {
    datasets.push({
      label: '2023',
      data: DATA.caMensuel["2023"],
      borderColor: '#818cf8',
      backgroundColor: 'rgba(129,140,248,0.10)',
      fill: true,
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 3,
      pointBackgroundColor: '#818cf8',
    });
  }
  if (show2024) {
    datasets.push({
      label: '2024',
      data: DATA.caMensuel["2024"],
      borderColor: '#a78bfa',
      backgroundColor: 'rgba(167,139,250,0.12)',
      fill: true,
      tension: 0.4,
      borderWidth: 2.5,
      pointRadius: 3,
      pointBackgroundColor: '#a78bfa',
    });
  }

  if (charts.caMensuel) charts.caMensuel.destroy();
  charts.caMensuel = new Chart(ctx, {
    type: 'line',
    data: { labels: DATA.caMensuel.labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: datasets.length > 1,
          position: 'top',
          align: 'end',
          labels: { boxWidth: 10, padding: 12, color: '#94a3b8', font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(148,163,184,0.2)',
          borderWidth: 1,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label} : ${fmt.euro(ctx.raw)}`,
          }
        }
      },
      scales: {
        x: { grid: { color: GRID_COLOR }, ticks: { color: '#64748b' } },
        y: {
          grid: { color: GRID_COLOR },
          ticks: {
            color: '#64748b',
            callback: v => v >= 1000 ? `${(v/1000).toFixed(0)}k€` : v
          }
        }
      }
    }
  });
}

// ── Graphique 2 : Catégories ─────────────────────────────────
function buildCategories() {
  const ctx = document.getElementById('chart-categories');
  if (!ctx) return;

  if (charts.categories) charts.categories.destroy();
  charts.categories = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: DATA.categories.labels,
      datasets: [{
        data: DATA.categories.ca,
        backgroundColor: [
          'rgba(129,140,248,0.7)',
          'rgba(56,189,248,0.7)',
          'rgba(52,211,153,0.7)',
          'rgba(251,146,60,0.7)',
          'rgba(248,113,113,0.7)',
        ],
        borderColor: ['#818cf8','#38bdf8','#34d399','#fb923c','#f87171'],
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(148,163,184,0.2)',
          borderWidth: 1,
          callbacks: { label: ctx => ` CA : ${fmt.euro(ctx.raw)}` }
        }
      },
      scales: {
        x: {
          grid: { color: GRID_COLOR },
          ticks: { callback: v => `${(v/1000).toFixed(0)}k€`, color: '#64748b' }
        },
        y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
      }
    }
  });
}

// ── Graphique 3 : Canaux ─────────────────────────────────────
function buildCanaux() {
  const ctx = document.getElementById('chart-canaux');
  if (!ctx) return;

  if (charts.canaux) charts.canaux.destroy();
  charts.canaux = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: DATA.canaux.labels,
      datasets: [{
        data: DATA.canaux.ca,
        backgroundColor: ['rgba(129,140,248,0.75)','rgba(56,189,248,0.75)',
                          'rgba(52,211,153,0.75)','rgba(251,146,60,0.75)'],
        borderColor: ['#818cf8','#38bdf8','#34d399','#fb923c'],
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: { boxWidth: 10, padding: 8, color: '#94a3b8', font: { size: 10 } }
        },
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(148,163,184,0.2)',
          borderWidth: 1,
          callbacks: {
            label: ctx => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct   = (ctx.raw / total * 100).toFixed(1);
              return ` ${ctx.label} : ${fmt.euro(ctx.raw)} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// ── Graphique 4 : Régions ─────────────────────────────────────
function buildRegions() {
  const ctx = document.getElementById('chart-regions');
  if (!ctx) return;

  if (charts.regions) charts.regions.destroy();
  charts.regions = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: DATA.regions.labels,
      datasets: [{
        data: DATA.regions.ca,
        backgroundColor: 'rgba(56,189,248,0.25)',
        borderColor: '#38bdf8',
        borderWidth: 1.5,
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(148,163,184,0.2)',
          borderWidth: 1,
          callbacks: { label: ctx => ` CA : ${fmt.euro(ctx.raw)}` }
        }
      },
      scales: {
        x: {
          grid: { color: GRID_COLOR },
          ticks: { callback: v => `${(v/1000).toFixed(0)}k€`, color: '#64748b' }
        },
        y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } }
      }
    }
  });
}

// ── Graphique 5 : Segments ────────────────────────────────────
function buildSegments() {
  const ctx = document.getElementById('chart-segments');
  if (!ctx) return;

  if (charts.segments) charts.segments.destroy();
  charts.segments = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: DATA.segments.labels,
      datasets: [{
        data: DATA.segments.ltv,
        backgroundColor: DATA.segments.colors.map(c => c + '55'),
        borderColor: DATA.segments.colors,
        borderWidth: 1.5,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          backgroundColor: '#1e293b',
          borderColor: 'rgba(148,163,184,0.2)',
          borderWidth: 1,
          callbacks: { label: ctx => ` LTV : ${fmt.euro(ctx.raw)}` }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 } } },
        y: { grid: { color: GRID_COLOR }, ticks: { callback: v => `${v}€`, color: '#64748b' } }
      }
    }
  });
}

// ── Tableau Top Produits ──────────────────────────────────────
function buildTopProduits() {
  const tbody = document.getElementById('top-produits-body');
  if (!tbody) return;

  const maxCA = Math.max(...DATA.topProduits.map(p => p.ca));

  tbody.innerHTML = DATA.topProduits.map(p => {
    const rankClass = p.rang <= 3 ? `rank-${p.rang}` : 'rank-n';
    const pct = (p.ca / maxCA * 100).toFixed(0);
    return `
      <tr>
        <td><span class="rank-badge ${rankClass}">${p.rang}</span></td>
        <td style="color:#f1f5f9; font-weight:600;">${p.nom}</td>
        <td><span style="color:#818cf8; font-size:0.75rem;">${p.cat}</span></td>
        <td style="color:#f1f5f9; font-weight:700;">${fmt.euro(p.ca)}</td>
        <td>${fmt.num(p.vol)}</td>
        <td>${fmt.euro(p.marge)}</td>
        <td><span style="color:#34d399; font-weight:600;">${p.taux}%</span></td>
        <td>
          <div class="perf-bar">
            <div class="perf-bar-bg">
              <div class="perf-bar-fill" style="width:${pct}%"></div>
            </div>
            <span class="perf-pct">${pct}%</span>
          </div>
        </td>
      </tr>`;
  }).join('');
}

// ── KPI Cards ─────────────────────────────────────────────────
function updateKPIs(annee) {
  const d = DATA.kpis[annee] || DATA.kpis['all'];

  // Valeurs animées
  animateValue('kpi-ca-val',     0, d.ca,            1200, fmt.euro);
  animateValue('kpi-panier-val', 0, d.panier,         800, v => fmt.euro(v));
  animateValue('kpi-marge-val',  0, d.marge,           800, v => v.toFixed(1) + '%');
  animateValue('kpi-tx-val',     0, d.transactions,   1000, fmt.num);

  // Sous-titres
  setText('kpi-ca-sub',     annee === 'all' ? '2 ans cumulés' : `Exercice ${annee}`);
  setText('kpi-panier-sub', 'Valeur moy. par transaction');
  setText('kpi-marge-sub',  'Marge brute / CA HT');
  setText('kpi-tx-sub',     'Nombre de ventes');
}

function animateValue(id, start, end, duration, formatFn) {
  const el = document.getElementById(id);
  if (!el) return;
  const startTime = performance.now();
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = formatFn(start + (end - start) * eased);
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ── Timestamp ─────────────────────────────────────────────────
function updateTimestamp() {
  const el = document.getElementById('refresh-time');
  if (el) el.textContent = new Date().toLocaleTimeString('fr-FR');
}

// ── Mise à jour globale ───────────────────────────────────────
function updateDashboard() {
  const annee = document.getElementById('filter-annee')?.value || 'all';
  updateKPIs(annee);
  buildCaMensuel(annee);
}

function refreshData() {
  const icon = document.getElementById('refresh-icon');
  if (icon) {
    icon.style.display = 'inline-block';
    icon.style.animation = 'spin 0.6s linear';
    setTimeout(() => { icon.style.animation = ''; }, 600);
  }
  updateTimestamp();
  updateDashboard();
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Ajouter keyframe spin dynamiquement
  const style = document.createElement('style');
  style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(style);

  updateTimestamp();
  updateDashboard();
  buildCategories();
  buildCanaux();
  buildRegions();
  buildSegments();
  buildTopProduits();
});
