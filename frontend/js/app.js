/* =========================
   UTILITARIOS E CONFIG
   ========================= */
const API_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws';

// Formata valor para Real Brasileiro
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

// Formata data para DD/MM/AAAA
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

// Mostra notificações (Toast)
function showToast(message, type = 'primary') {
    const toast = document.createElement('div');
    toast.className = `toast btn-${type}`;
    toast.innerText = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Verifica se o usuário está logado
async function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        if (!window.location.pathname.includes('login.html') && !window.location.pathname.includes('register.html')) {
            window.location.href = 'login.html';
        }
        return;
    }

    try {
        const response = await fetch(`${API_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
            logout();
        } else {
            const user = await response.json();
            const greeting = document.getElementById('userGreeting');
            if (greeting) greeting.innerText = `Olá, ${user.name}`;
            return user;
        }
    } catch (err) {
        console.error('Erro de autenticação', err);
        logout();
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
}

/* =========================
   WEBSOCKET SYNC
   ========================= */
let socket = null;

function setupWebSocket(roomId) {
    if (!roomId || socket) return;
    
    socket = new WebSocket(`${WS_URL}/${roomId}`);
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Mensagem recebida via WS:', data);
        showToast('Dados atualizados pela parceira', 'success');
        
        // Recarregar dados da página atual se necessário
        if (typeof loadDashboardData === 'function') loadDashboardData();
        if (typeof loadTransactions === 'function') loadTransactions();
    };

    socket.onclose = () => {
        socket = null;
        setTimeout(() => setupWebSocket(roomId), 5000);
    };
}

function notifySync(roomId, type, payload = {}) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(json.stringify({ type, ...payload }));
    }
}
