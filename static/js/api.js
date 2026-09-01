const API = {
    baseUrl: '/api',
    tokens: JSON.parse(localStorage.getItem('mh_tokens') || 'null'),
    user: JSON.parse(localStorage.getItem('mh_user') || 'null'),

    setAuth(tokens, user) {
        this.tokens = tokens;
        this.user = user;
        if (tokens) localStorage.setItem('mh_tokens', JSON.stringify(tokens));
        else localStorage.removeItem('mh_tokens');
        if (user) localStorage.setItem('mh_user', JSON.stringify(user));
        else localStorage.removeItem('mh_user');
        $(document).trigger('auth:change', [this.user]);
    },

    isLoggedIn() { return !!this.tokens?.access; },

    async request(method, url, data, isFormData = false) {
        const opts = {
            method,
            url: this.baseUrl + url,
            headers: {},
        };
        if (this.tokens?.access) {
            opts.headers['Authorization'] = `Bearer ${this.tokens.access}`;
        }
        if (data) {
            if (isFormData) {
                opts.data = data;
            } else {
                opts.headers['Content-Type'] = 'application/json';
                opts.data = JSON.stringify(data);
            }
        }
        const res = await fetch(opts.url, opts);
        const text = await res.text();
        let json = null;
        try { json = text ? JSON.parse(text) : null; } catch (e) {}

        if (!res.ok) {
            // Попробовать обновить токен при 401
            if (res.status === 401 && this.tokens?.refresh && method !== 'POST') {
                const refreshed = await this.refreshAccessToken();
                if (refreshed) return this.request(method, url, data, isFormData);
            }
            const err = new Error(json?.detail || json?.non_field_errors?.[0] || 'Ошибка запроса');
            err.status = res.status;
            err.data = json;
            throw err;
        }
        return json;
    },

    async refreshAccessToken() {
        try {
            const res = await fetch(this.baseUrl + '/auth/refresh/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({refresh: this.tokens.refresh}),
            });
            if (!res.ok) { this.setAuth(null, null); return false; }
            const data = await res.json();
            this.tokens.access = data.access;
            if (data.refresh) this.tokens.refresh = data.refresh;
            localStorage.setItem('mh_tokens', JSON.stringify(this.tokens));
            return true;
        } catch (e) {
            this.setAuth(null, null);
            return false;
        }
    },

    get(url) { return this.request('GET', url); },
    post(url, data, isFormData) { return this.request('POST', url, data, isFormData); },
    put(url, data, isFormData) { return this.request('PUT', url, data, isFormData); },
    patch(url, data, isFormData) { return this.request('PATCH', url, data, isFormData); },
    delete(url) { return this.request('DELETE', url); },
};