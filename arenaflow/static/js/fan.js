(() => {
    const city = document.getElementById('city');
    const scroll = document.getElementById('scroll');
    const composer = document.getElementById('composer');
    const q = document.getElementById('q');
    const send = document.getElementById('send');
    const status = document.getElementById('status');
    const langPill = document.getElementById('lang-pill');

    async function loadVenues() {
        try {
            const r = await fetch('/api/cities');
            const data = await r.json();
            for (const c of data.cities) {
                const opt = document.createElement('option');
                opt.value = c.city; opt.textContent = c.label;
                city.appendChild(opt);
            }
        } catch (e) { /* non-fatal */ }
    }

    function addMsg(role, text, meta) {
        const wrap = document.createElement('div');
        wrap.className = 'msg ' + role;
        const b = document.createElement('div');
        b.className = 'bubble';
        b.textContent = text;
        if (meta) {
            const m = document.createElement('div');
            m.className = 'meta';
            m.textContent = meta;
            b.appendChild(m);
        }
        wrap.appendChild(b);
        scroll.appendChild(wrap);
        scroll.scrollTop = scroll.scrollHeight;
    }

    async function ask(query) {
        if (!city.value) {
            addMsg('bot', 'Please select a host city first.');
            return;
        }
        if (!query.trim()) return;
        addMsg('user', query);
        q.value = '';
        send.disabled = true;
        status.textContent = 'Thinking...';
        try {
            const r = await fetch('/api/fan/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query, city: city.value || null}),
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const data = await r.json();
            const meta = `${data.source}${data.model ? ' (' + data.model + ')' : ''} - refs: ${data.used_ids.join(', ') || 'none'}`;
            addMsg('bot', data.text, meta);
            langPill.textContent = 'Detected language: ' + data.language;
            if (data.language) document.documentElement.lang = data.language;
            status.textContent = 'Ready.';
        } catch (e) {
            addMsg('bot', 'Sorry, something went wrong. Please try again.');
            status.textContent = 'Error: ' + e.message;
        } finally {
            send.disabled = false;
            q.focus();
        }
    }

    composer.addEventListener('submit', (e) => {
        e.preventDefault();
        ask(q.value);
    });

    document.querySelectorAll('.suggest button').forEach(btn => {
        btn.addEventListener('click', () => ask(btn.dataset.q));
    });

    loadVenues();
})();
