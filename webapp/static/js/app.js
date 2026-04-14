function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
}

async function apiAction(url, method = 'POST', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const csrf = getCookie('csrf_token');
    if (csrf) headers['X-CSRF-Token'] = csrf;
    const opts = { method, headers, credentials: 'same-origin' };
    if (body) opts.body = JSON.stringify(body);
    let res;
    try {
        res = await fetch(url, opts);
    } catch (e) {
        alert('Tarmoq xatosi');
        return null;
    }
    if (res.status === 401) { window.location.href = '/login'; return null; }
    if (!res.ok) {
        let msg = 'Xatolik yuz berdi';
        try {
            const data = await res.json();
            if (data?.detail) msg = data.detail;
            else if (data?.error) msg = data.error;
        } catch (_) { /* ignore */ }
        alert(msg);
        return null;
    }
    return await res.json();
}

async function logout() {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/logout';
    document.body.appendChild(form);
    form.submit();
}

// ── Drivers ──
async function driverAction(driverId, action) {
    const r = await apiAction(`/api/drivers/${driverId}/${action}`);
    if (r?.ok) location.reload();
}

async function deleteDriver(driverId) {
    if (!confirm("O'chirmoqchimisiz?")) return;
    const r = await apiAction(`/api/drivers/${driverId}`, 'DELETE');
    if (r?.ok) window.location.href = '/drivers';
}

// ── Trips ──
async function tripAction(tripId, action) {
    if (action === 'cancel' && !confirm("Bekor qilmoqchimisiz?")) return;
    const r = await apiAction(`/api/trips/${tripId}/${action}`);
    if (r?.ok) location.reload();
}

// ── Routes ──
async function routeToggle(routeId) {
    const r = await apiAction(`/api/routes/${routeId}/toggle`);
    if (r?.ok) location.reload();
}

async function routeDelete(routeId) {
    if (!confirm("O'chirmoqchimisiz?")) return;
    const r = await apiAction(`/api/routes/${routeId}`, 'DELETE');
    if (r?.ok) location.reload();
}

// ── Users ──
async function userAction(userId, action) {
    const r = await apiAction(`/api/users/${userId}/${action}`);
    if (r?.ok) location.reload();
}

async function deleteUser(userId) {
    if (!confirm("O'chirmoqchimisiz?")) return;
    const r = await apiAction(`/api/users/${userId}`, 'DELETE');
    if (r?.ok) window.location.href = '/users';
}

// ── Modal ──
function showModal(id) { document.getElementById(id).classList.add('show'); }
function hideModal(id) { document.getElementById(id).classList.remove('show'); }

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) e.target.classList.remove('show');
});
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
        closeSidebar();
    }
});

// ── Mobile sidebar drawer ──
function openSidebar() {
    document.getElementById('sidebar')?.classList.add('open');
    document.getElementById('sidebarOverlay')?.classList.add('show');
}
function closeSidebar() {
    document.getElementById('sidebar')?.classList.remove('open');
    document.getElementById('sidebarOverlay')?.classList.remove('show');
}
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('menuBtn')?.addEventListener('click', openSidebar);
    document.getElementById('sidebarOverlay')?.addEventListener('click', closeSidebar);
    document.querySelectorAll('.sidebar a').forEach(a => a.addEventListener('click', closeSidebar));
});
