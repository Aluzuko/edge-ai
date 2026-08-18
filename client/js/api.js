// Thin fetch wrapper. Mirrors what ApiService did in the Angular app.
const Api = {
  async get(path, params) {
    const url = new URL(API_BASE_URL + path);
    if (params) {
      for (const key of Object.keys(params)) {
        const value = params[key];
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, value);
        }
      }
    }
    const resp = await fetch(url.toString());
    if (!resp.ok) {
      throw await Api._error(resp);
    }
    return resp.json();
  },

  async post(path, body) {
    const isFormData = body instanceof FormData;
    const resp = await fetch(API_BASE_URL + path, {
      method: 'POST',
      headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
      body: isFormData ? body : JSON.stringify(body)
    });
    if (!resp.ok) {
      throw await Api._error(resp);
    }
    return resp.json();
  },

  async patch(path, body) {
    const resp = await fetch(API_BASE_URL + path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
    if (!resp.ok) {
      throw await Api._error(resp);
    }
    return resp.json();
  },

  fileUrl(path) {
    return API_BASE_URL + path;
  },

  async _error(resp) {
    let detail = 'Request failed with status ' + resp.status;
    try {
      const body = await resp.json();
      if (body && body.detail) {
        detail = body.detail;
      }
    } catch (_) {
      // response wasn't JSON, keep default message
    }
    return new Error(detail);
  }
};

// Shared small helpers used across pages.
const Fmt = {
  date(value) {
    if (!value) return '';
    const d = new Date(value);
    return isNaN(d.getTime()) ? '' : d.toLocaleString();
  },
  percent(value) {
    return value != null ? (value * 100).toFixed(1) + '%' : '';
  },
  number(value, digits) {
    return value != null ? value.toFixed(digits) : '';
  },
  escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }
};
