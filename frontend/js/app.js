/*
   FUNÇÕES GLOBAIS - autenticação, API, utilitários e toast
   ===================================================== */
const API_URL = window.SYNCUS_API_URL || 'http://localhost:8000/api';

function getStoredToken() {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
}

function storeAuthToken(token, remember = true) {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    (remember ? localStorage : sessionStorage).setItem('token', token);
}

class ApiError extends Error {
    constructor(message, status = 0, data = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

function authHeaders(extra = {}) {
    const token = getStoredToken();
    return {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...extra
    };
}

async function apiRequest(path, options = {}) {
    const { auth = true, body, headers = {}, ...requestOptions } = options;
    const finalHeaders = auth ? authHeaders(headers) : { ...headers };
    let finalBody = body;

    if (body !== undefined && body !== null && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof URLSearchParams) && !(body instanceof Blob)) {
        finalBody = JSON.stringify(body);
        if (!finalHeaders['Content-Type']) finalHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_URL}${path}`, {
        ...requestOptions,
        headers: finalHeaders,
        body: finalBody
    });

    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json')
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        const detail = Array.isArray(data?.detail)
            ? data.detail.map(item => item.msg || item.message).join(', ')
            : data?.detail || data?.message || data || `Erro HTTP ${response.status}`;
        throw new ApiError(detail, response.status, data);
    }

    return data;
}

function isAuthError(error) {
    return error?.status === 401 || error?.status === 403;
}

function handleApiError(error, fallback = 'Não foi possível concluir a operação.') {
    if (isAuthError(error)) {
        logout();
        return 'Sua sessão expirou. Faça login novamente.';
    }
    return error?.message || fallback;
}

function downloadTextFile(filename, content, mime = 'text/plain;charset=utf-8') {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

// =========================
// AUTENTICAÇÃO
// =========================
async function checkAuth() {
    const token = getStoredToken();
    if (!token) {
        window.location.href = 'login.html';
        return null;
    }

    try {
        const user = await apiRequest('/users/me');
        localStorage.setItem('user', JSON.stringify(user));
        return user;
    } catch (error) {
        logout();
        return null;
    }
}

function logout() {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'login.html';
}

// =========================
// UTILITÁRIOS DE FORMATAÇÃO
// =========================
function formatCurrency(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(Number(valor) || 0);
}

function formatDate(data) {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
}

function toInputDate(data = new Date()) {
    const date = new Date(data);
    const offset = date.getTimezoneOffset();
    return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function toApiDate(dateValue) {
    if (!dateValue) return null;
    return dateValue.length === 10 ? `${dateValue}T12:00:00` : dateValue;
}

function iniciaisDoNome(nome) {
    if (!nome) return '??';
    return nome
        .trim()
        .split(' ')
        .filter(p => p.length > 0)
        .slice(0, 2)
        .map(p => p[0].toUpperCase())
        .join('');
}

// =========================
// TOAST (MENSAGENS)
// =========================
function showToast(mensagem, tipo = 'info') {
    const cores = {
        success: 'linear-gradient(135deg,#059669,#10B981)',
        danger: 'linear-gradient(135deg,#DC2626,#EF4444)',
        warning: 'linear-gradient(135deg,#D97706,#F59E0B)',
        info: 'linear-gradient(135deg,#2563EB,#3B82F6)'
    };

    const t = document.createElement('div');
    t.className = 'toast-sync';
    t.style.background = cores[tipo] || cores.info;
    t.textContent = mensagem;
    document.body.appendChild(t);

    setTimeout(() => {
        t.style.transition = 'opacity .3s, transform .3s';
        t.style.opacity = '0';
        t.style.transform = 'translateX(120%)';
        setTimeout(() => t.remove(), 300);
    }, 3200);
}
