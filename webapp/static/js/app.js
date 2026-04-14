async function apiAction(url, method = 'POST', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    if (!res.ok) { alert('Xatolik yuz berdi'); return null; }
    return await res.json();
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
    if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
});
