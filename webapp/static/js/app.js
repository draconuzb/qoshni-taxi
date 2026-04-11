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
    if (!confirm("Haydovchini o'chirmoqchimisiz? Bu qaytarib bo'lmaydi!")) return;
    const r = await apiAction(`/api/drivers/${driverId}`, 'DELETE');
    if (r?.ok) window.location.href = '/drivers';
}

// ── Orders ──
async function orderCancel(orderId) {
    if (!confirm('Buyurtmani bekor qilmoqchimisiz?')) return;
    const r = await apiAction(`/api/orders/${orderId}/cancel`);
    if (r?.ok) location.reload();
}

async function orderComplete(orderId) {
    const r = await apiAction(`/api/orders/${orderId}/complete`);
    if (r?.ok) location.reload();
}

// ── Trips ──
async function tripAction(tripId, action) {
    if (action === 'cancel' && !confirm('Safarni bekor qilmoqchimisiz?')) return;
    const r = await apiAction(`/api/trips/${tripId}/${action}`);
    if (r?.ok) location.reload();
}

// ── Routes ──
async function routeToggle(routeId) {
    const r = await apiAction(`/api/routes/${routeId}/toggle`);
    if (r?.ok) location.reload();
}

async function routeDelete(routeId) {
    if (!confirm("Yo'nalishni o'chirmoqchimisiz?")) return;
    const r = await apiAction(`/api/routes/${routeId}`, 'DELETE');
    if (r?.ok) location.reload();
}

// ── Users ──
async function userAction(userId, action) {
    const r = await apiAction(`/api/users/${userId}/${action}`);
    if (r?.ok) location.reload();
}

async function deleteUser(userId) {
    if (!confirm("Foydalanuvchini o'chirmoqchimisiz? Bu qaytarib bo'lmaydi!")) return;
    const r = await apiAction(`/api/users/${userId}`, 'DELETE');
    if (r?.ok) window.location.href = '/users';
}

// ── Modal ──
function showModal(id) {
    document.getElementById(id).classList.add('show');
}

function hideModal(id) {
    document.getElementById(id).classList.remove('show');
}

// Close modals on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('show');
    }
});

// Close modals on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
    }
});
