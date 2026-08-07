/* =====================================================
   ✅ FUNÇÕES GLOBAIS - auth, utils, toast
   ===================================================== */
const API_URL = 'http://localhost:8000/api';

// =========================
// AUTENTICAÇÃO
// =========================
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = 'login.html'; return null; }

    try {
        const res = await fetch(`${API_URL}/users/me`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) { logout(); return null; }
        return await res.json();
    } catch (err) { logout(); return null; }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}

// =========================
// UTILITÁRIOS DE FORMATAÇÃO
// =========================
function formatCurrency(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor || 0);
}

function formatDate(data) {
    return new Date(data).toLocaleDateString('pt-BR');
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
        danger:  'linear-gradient(135deg,#DC2626,#EF4444)',
        warning: 'linear-gradient(135deg,#D97706,#F59E0B)',
        info:    'linear-gradient(135deg,#2563EB,#3B82F6)'
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