(() => {
    const venue = document.getElementById('venue');
    const minute = document.getElementById('minute');
    const refresh = document.getElementById('refresh');
    const askBtn = document.getElementById('ask');
    const q = document.getElementById('q');
    const answer = document.getElementById('answer');
    const meta = document.getElementById('meta');
    const kpiInside = document.getElementById('kpi-inside');
    const kpiPct = document.getElementById('kpi-pct');
    const kpiWeather = document.getElementById('kpi-weather');
    const kpiAq = document.getElementById('kpi-aq');
    const kpiBusiest = document.getElementById('kpi-busiest');
    const kpiBusiestGate = document.getElementById('kpi-busiest-gate');
    const gatesBody = document.querySelector('#gates tbody');
    const transit = document.getElementById('transit');
    const alerts = document.getElementById('alerts');
    const langPill = document.getElementById('lang-pill');

    function pillFor(status) {
        const span = document.createElement('span');
        span.className = 'pill ' + (status === 'open' ? 'good' : status === 'busy' ? 'warn' : 'bad');
        span.textContent = status;
        return span;
    }

    // All values rendered via textContent/createElement - never innerHTML -
    // so any untrusted/ model-influenced text cannot execute as HTML.
    function renderSnapshot(s) {
        kpiInside.textContent = s.inside.toLocaleString();
        kpiPct.textContent = Math.round((s.inside / s.capacity) * 100);
        kpiWeather.textContent = s.weather;
        kpiAq.textContent = s.air_quality;

        const busy = s.gates.filter(g => g.status !== 'paused')
                            .sort((a, b) => b.wait_min - a.wait_min)[0];
        if (busy) {
            kpiBusiest.textContent = busy.wait_min + ' min';
            kpiBusiestGate.textContent = 'Gate ' + busy.gate;
        } else {
            kpiBusiest.textContent = '-';
            kpiBusiestGate.textContent = 'all gates paused';
        }

        gatesBody.replaceChildren();
        for (const g of s.gates) {
            const tr = document.createElement('tr');
            const tdGate = document.createElement('td'); tdGate.textContent = g.gate;
            const tdStatus = document.createElement('td'); tdStatus.appendChild(pillFor(g.status));
            const tdWait = document.createElement('td'); tdWait.textContent = g.wait_min;
            tr.append(tdGate, tdStatus, tdWait);
            gatesBody.appendChild(tr);
        }

        transit.replaceChildren();
        for (const [line, st] of Object.entries(s.transit_load || {})) {
            const p = document.createElement('div');
            const tag = document.createElement('span');
            tag.className = 'pill muted'; tag.textContent = line;
            p.append(tag, document.createTextNode(' ' + st));
            transit.appendChild(p);
        }
        if (s.sustainability) {
            for (const [k, v] of Object.entries(s.sustainability)) {
                const p = document.createElement('div');
                const tag = document.createElement('span');
                tag.className = 'pill'; tag.textContent = k.replace('_', ' ');
                p.append(tag, document.createTextNode(' ' + v));
                transit.appendChild(p);
            }
        }

        alerts.replaceChildren();
        if (!s.alerts || s.alerts.length === 0) {
            const p = document.createElement('p');
            p.className = 'lead'; p.textContent = 'No active alerts.';
            alerts.appendChild(p);
        } else {
            for (const a of s.alerts) {
                const d = document.createElement('div');
                d.className = 'alert';
                d.textContent = a;
                alerts.appendChild(d);
            }
        }
    }

    async function loadVenues() {
        const r = await fetch('/api/venues');
        const data = await r.json();
        for (const v of data.venues) {
            const opt = document.createElement('option');
            opt.value = v; opt.textContent = v;
            venue.appendChild(opt);
        }
        if (data.venues.length) {
            venue.value = data.venues[0];
            loadSnapshot();
        }
    }

    function clampMinute() {
        let m = parseInt(minute.value, 10);
        if (!Number.isFinite(m)) m = 60;
        return Math.max(0, Math.min(240, m));
    }

    async function loadSnapshot() {
        const m = clampMinute();
        const r = await fetch(`/api/ops/snapshot?venue=${encodeURIComponent(venue.value)}&minute=${m}`);
        const s = await r.json();
        renderSnapshot(s);
    }

    async function ask() {
        const question = q.value.trim();
        if (!question) return;
        answer.textContent = 'Thinking...';
        meta.textContent = '';
        askBtn.disabled = true;
        try {
            const r = await fetch('/api/ops/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    question,
                    venue: venue.value,
                    minute: clampMinute(),
                }),
            });
            const data = await r.json();
            answer.textContent = data.text;
            meta.textContent = `${data.source}${data.model ? ' (' + data.model + ')' : ''} - refs: ${data.used_ids.join(', ') || 'none'}`;
            if (data.language) document.documentElement.lang = data.language;
        } catch (e) {
            answer.textContent = 'Error: ' + e.message;
        } finally {
            askBtn.disabled = false;
        }
    }

    refresh.addEventListener('click', loadSnapshot);
    venue.addEventListener('change', loadSnapshot);
    minute.addEventListener('change', loadSnapshot);
    askBtn.addEventListener('click', ask);
    q.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) ask();
    });
    document.querySelectorAll('button[data-q]').forEach(b => {
        b.addEventListener('click', () => { q.value = b.dataset.q; ask(); });
    });

    loadVenues();
})();
