/* =====================================================
   ✅ UI - top bar, sidebar, sininho, gaveta, notificações
   ===================================================== */
let atualizaNotifTimer = null;

window.addEventListener('DOMContentLoaded', async () => {
    const user = await checkAuth();
    if (!user) return;

    preencherPerfilNaTopBar(user);
    ligarBotaoSidebar();
    ligarSininho();

    // Atualiza notificações a cada 10s
    await carregarNotificacoes();
    atualizaNotifTimer = setInterval(carregarNotificacoes, 10000);
});

// =========================
// SIDEBAR - abrir/fechar
// =========================
function ligarBotaoSidebar() {
    const btn = document.getElementById('btnMenu');
    const sidebar = document.getElementById('sidebar');
    if (!btn || !sidebar) return;

    btn.addEventListener('click', () => {
        sidebar.classList.toggle('fechada');
        sidebar.classList.toggle('aberta');
    });
}

// =========================
// PERFIL NA TOP BAR
// =========================
function preencherPerfilNaTopBar(user) {
    const inicial = iniciaisDoNome(user.name);
    if (document.getElementById('perfilFoto'))  document.getElementById('perfilFoto').textContent  = inicial;
    if (document.getElementById('perfilNome'))  document.getElementById('perfilNome').textContent  = user.name;
    if (document.getElementById('gavetaNome'))  document.getElementById('gavetaNome').textContent  = user.name;
    if (document.getElementById('gavetaEmail')) document.getElementById('gavetaEmail').textContent = user.email;
}

// =========================
// SININHO + NOTIFICAÇÕES
// =========================
function ligarSininho() {
    const btn = document.getElementById('marcarTodasLidas');
    if (btn) btn.addEventListener('click', marcarTodasLidas);
}

async function carregarNotificacoes() {
    const lista = document.getElementById('listaNotif');
    const cont  = document.getElementById('contadorNotif');
    if (!lista) return;

    try {
        // ✅ CERTO: /api/couple/notifications
        const res = await fetch(`${API_URL}/couple/notifications`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        // ... resto da função continua igual ...
    } catch(e){}
}

async function aceitarConvite(id) {
    if (!confirm('Aceitar vínculo?')) return;
    // ✅ CERTO: /api/couple/invite/{id}/accept
    const r = await fetch(`${API_URL}/couple/invite/${id}/accept`, {
        method:'POST', headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
    });
    if (r.ok) { showToast('🎉 Vínculo aprovado!','success'); setTimeout(()=>location.reload(),1100); }
}
window.aceitarConvite = aceitarConvite;

async function recusarConvite(id) {
    if (!confirm('Recusar vínculo?')) return;
    // ✅ CERTO: /api/couple/invite/{id}/reject
    await fetch(`${API_URL}/couple/invite/${id}/reject`, {
        method:'POST', headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
    });
    showToast('Convite recusado','warning');
    carregarNotificacoes();
}
window.recusarConvite = recusarConvite;

async function marcarTodasLidas() {
    try {
        await fetch(`${API_URL}/couple/notifications/read-all`, {
            method: 'PUT',
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        carregarNotificacoes();
        showToast('Todas marcadas como lidas','success');
    } catch(e){}
}

async function aceitarConvite(id) {
    if (!confirm('✅ Aceitar esse vínculo?')) return;
    const r = await fetch(`${API_URL}/couple/invite/${id}/accept`, {
        method:'POST', headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
    });
    if (r.ok) {
        showToast('🎉 Vínculo aprovado!','success');
        setTimeout(() => location.reload(), 1200);
    }
}

async function recusarConvite(id) {
    if (!confirm('❌ Recusar esse vínculo?')) return;
    await fetch(`${API_URL}/couple/invite/${id}/reject`, {
        method:'POST', headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
    });
    showToast('Convite recusado','warning');
    carregarNotificacoes();
}