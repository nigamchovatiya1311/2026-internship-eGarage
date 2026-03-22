/* E-GARAGE ADMIN DASHBOARD — admin-dashboard.js */

/* ── SIDEBAR ── */
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const hamburgerBtn   = document.getElementById('hamburgerBtn');
const sidebarClose   = document.getElementById('sidebarClose');
hamburgerBtn.addEventListener('click', () => { sidebar.classList.toggle('open'); sidebarOverlay.classList.toggle('open'); });
sidebarClose.addEventListener('click', closeSidebar);
sidebarOverlay.addEventListener('click', closeSidebar);
function closeSidebar() { sidebar.classList.remove('open'); sidebarOverlay.classList.remove('open'); }

/* ── NAVIGATION ── */
const sectionNames = {
  overview:'Overview', users:'Manage Users', providers:'Service Providers',
  customers:'Customer Profiles', services:'Services', bookings:'Monitor Bookings',
  payments:'Payments', invoices:'Invoices', reviews:'Reviews',
  notifications:'Notifications', disputes:'Disputes', analytics:'Analytics', reports:'Generate Reports'
};
document.querySelectorAll('.nav-item[data-section]').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    switchSection(item.getAttribute('data-section'));
    if (window.innerWidth <= 900) closeSidebar();
  });
});
function switchSection(target) {
  document.querySelectorAll('.nav-item[data-section]').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.dash-section').forEach(s => s.classList.remove('active'));
  const nav = document.querySelector(`.nav-item[data-section="${target}"]`);
  const sec = document.getElementById(`sec-${target}`);
  if (nav) nav.classList.add('active');
  if (sec) sec.classList.add('active');
  const bc = document.getElementById('breadCurrent');
  if (bc) bc.textContent = sectionNames[target] || target;
  animateCounters();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── COUNTERS ── */
function animateCounters() {
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target   = parseInt(el.getAttribute('data-target'));
    const prefix   = el.getAttribute('data-prefix') || '';
    const suffix   = el.getAttribute('data-suffix') || '';
    const duration = 1200;
    const start    = Date.now();
    const tick = () => {
      const p    = Math.min((Date.now() - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + Math.floor(ease * target).toLocaleString('en-IN') + suffix;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}
window.addEventListener('load', animateCounters);

/* ── FILTER TABS (generic) ── */
function filterTab(btn, role, tableId) {
  btn.closest('.filter-tabs').querySelectorAll('.ftab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const table = document.getElementById(tableId);
  if (!table) return;
  table.querySelectorAll('tbody tr').forEach(row => {
    row.style.display = (role === 'all' || row.dataset.role === role) ? '' : 'none';
  });
}

/* ── SEARCH (generic) ── */
function searchTable(input, tableId) {
  const q = input.value.toLowerCase();
  const table = document.getElementById(tableId);
  if (!table) return;
  table.querySelectorAll('tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

/* ── FILTER BY STATUS ── */
function filterByStatus(select, tableId) {
  const status = select.value;
  const table = document.getElementById(tableId);
  if (!table) return;
  table.querySelectorAll('tbody tr').forEach(row => {
    row.style.display = (!status || row.dataset.status === status) ? '' : 'none';
  });
}

/* ── SELECT ALL ── */
function toggleSelectAll(master, tableId) {
  const table = document.getElementById(tableId);
  if (table) table.querySelectorAll('.row-check').forEach(cb => cb.checked = master.checked);
}

/* ── USER MODAL ── */
function showUserModal(name, email, role, status, mobile, joined, gender) {
  const sc = status === 'Active' ? 'success' : status === 'Blocked' ? 'danger' : 'warning';
  document.getElementById('userModalBody').innerHTML = `
    <div class="modal-detail-row"><span>Full Name</span><span>${name}</span></div>
    <div class="modal-detail-row"><span>Email</span><span>${email}</span></div>
    <div class="modal-detail-row"><span>Mobile</span><span>${mobile}</span></div>
    <div class="modal-detail-row"><span>Gender</span><span>${gender}</span></div>
    <div class="modal-detail-row"><span>Role</span><span>${role}</span></div>
    <div class="modal-detail-row"><span>Status</span><span><span class="badge ${sc}">${status}</span></span></div>
    <div class="modal-detail-row"><span>Joined</span><span>${joined}</span></div>`;
  openModal('userModal');
}

/* ── PROVIDER MODAL ── */
function showProviderModal(name, location, hours, rating, approval, services) {
  const sc = approval === 'Approved' ? 'success' : approval === 'Rejected' ? 'danger' : 'warning';
  document.getElementById('providerModalBody').innerHTML = `
    <div class="modal-detail-row"><span>Garage Name</span><span>${name}</span></div>
    <div class="modal-detail-row"><span>Location</span><span>${location}</span></div>
    <div class="modal-detail-row"><span>Operating Hours</span><span>${hours}</span></div>
    <div class="modal-detail-row"><span>Rating</span><span>${rating === '—' ? '—' : `⭐ ${rating}`}</span></div>
    <div class="modal-detail-row"><span>Approval Status</span><span><span class="badge ${sc}">${approval}</span></span></div>
    <div class="modal-detail-row"><span>Services Offered</span><span>${services}</span></div>`;
  openModal('providerModal');
}

/* ── CUSTOMER MODAL ── */
function showCustomerModal(name, vType, vNum, vModel, vYear, vColor) {
  document.getElementById('customerModalBody').innerHTML = `
    <div class="modal-detail-row"><span>Customer Name</span><span>${name}</span></div>
    <div class="modal-detail-row"><span>Vehicle Type</span><span>${vType}</span></div>
    <div class="modal-detail-row"><span>Vehicle Number</span><span><strong>${vNum}</strong></span></div>
    <div class="modal-detail-row"><span>Vehicle Model</span><span>${vModel}</span></div>
    <div class="modal-detail-row"><span>Year</span><span>${vYear}</span></div>
    <div class="modal-detail-row"><span>Color</span><span>${vColor}</span></div>`;
  openModal('customerModal');
}

/* ── BOOKING MODAL ── */
function showBookingModal(id, cust, svc, prov, date, time, amount, status, vehicle) {
  const sc = status === 'Completed' ? 'success' : status === 'Cancelled' ? 'danger' : status === 'Pending' ? 'warning' : 'info';
  document.getElementById('bookingModalBody').innerHTML = `
    <div class="modal-detail-row"><span>Booking ID</span><span><strong>${id}</strong></span></div>
    <div class="modal-detail-row"><span>Customer</span><span>${cust}</span></div>
    <div class="modal-detail-row"><span>Vehicle No.</span><span>${vehicle}</span></div>
    <div class="modal-detail-row"><span>Service</span><span>${svc}</span></div>
    <div class="modal-detail-row"><span>Provider</span><span>${prov}</span></div>
    <div class="modal-detail-row"><span>Booking Date</span><span>${date}</span></div>
    <div class="modal-detail-row"><span>Booking Time</span><span>${time}</span></div>
    <div class="modal-detail-row"><span>Amount</span><span><strong>${amount}</strong></span></div>
    <div class="modal-detail-row"><span>Status</span><span><span class="badge ${sc}">${status}</span></span></div>`;
  openModal('bookingModal');
}

/* ── SERVICE MODAL ── */
function openServiceModal(name = '', desc = '', price = '', duration = '', provider = '') {
  document.getElementById('serviceModalTitle').innerHTML = `<i class="fas fa-tags"></i> ${name ? 'Edit Service' : 'Add Service'}`;
  document.getElementById('svcName').value      = name;
  document.getElementById('svcDesc').value      = desc;
  document.getElementById('svcPrice').value     = price;
  document.getElementById('svcDuration').value  = duration;
  document.getElementById('svcProvider').value  = provider;
  openModal('serviceModal');
}
function saveService() {
  const name = document.getElementById('svcName').value.trim();
  if (!name) { showToast('Please enter a service name', 'warning'); return; }
  closeModal('serviceModal');
  showToast('Service saved successfully', 'success');
}

/* ── NOTIFICATION MODAL ── */
function openNotifModal() { openModal('notifModal'); }
function sendNotification() {
  const title = document.getElementById('notifTitle').value.trim();
  const msg   = document.getElementById('notifMsg').value.trim();
  if (!title || !msg) { showToast('Please fill in title and message', 'warning'); return; }
  closeModal('notifModal');
  showToast('Notification sent successfully', 'success');
}

/* ── DELETE ── */
function confirmDelete(type, name) {
  document.getElementById('deleteMsg').innerHTML = `Are you sure you want to delete <strong>${name}</strong>?<br/><span style="color:#dc2626;font-size:0.82rem">This action cannot be undone.</span>`;
  openModal('deleteModal');
}

/* ── PROVIDER APPROVE ── */
function approveProvider(btn, name) {
  const item = btn.closest('.approval-item') || btn.closest('tr');
  if (!item) return;
  const badge = item.querySelector('.badge');
  if (badge) { badge.className = 'badge success'; badge.textContent = 'Approved'; }
  btn.remove();
  showToast(`${name} approved successfully`, 'success');
}

/* ── USER ACTIONS ── */
function approveUser(btn) {
  const row = btn.closest('tr');
  row.querySelector('.badge').className = 'badge success';
  row.querySelector('.badge').textContent = 'Active';
  row.dataset.status = 'active';
  btn.remove();
  showToast('User approved successfully', 'success');
}
function blockUser(btn) {
  const row = btn.closest('tr');
  row.querySelector('.badge').className = 'badge danger';
  row.querySelector('.badge').textContent = 'Blocked';
  row.dataset.status = 'blocked';
  btn.innerHTML = '<i class="fas fa-unlock"></i>';
  btn.classList.remove('block');
  btn.classList.add('unblock');
  btn.setAttribute('onclick', 'unblockUser(this)');
  showToast('User blocked', 'danger');
}
function unblockUser(btn) {
  const row = btn.closest('tr');
  row.querySelector('.badge').className = 'badge success';
  row.querySelector('.badge').textContent = 'Active';
  row.dataset.status = 'active';
  btn.innerHTML = '<i class="fas fa-ban"></i>';
  btn.classList.remove('unblock');
  btn.classList.add('block');
  btn.setAttribute('onclick', 'blockUser(this)');
  showToast('User unblocked', 'success');
}

/* ── DISPUTES ── */
function resolveDispute(btn, id) {
  const card = btn.closest('.dispute-card');
  card.classList.remove('open', 'review');
  card.classList.add('resolved');
  const badge = card.querySelector('.badge');
  badge.className = 'badge success';
  badge.textContent = 'Resolved';
  btn.remove();
  showToast(`Dispute ${id} marked as resolved`, 'success');
}
function closeDispute(btn) {
  const card = btn.closest('.dispute-card');
  card.style.transition = 'all 0.3s ease';
  card.style.opacity = '0';
  card.style.transform = 'translateX(20px)';
  setTimeout(() => card.remove(), 300);
  showToast('Dispute closed', 'success');
}

/* ── REPORTS ── */
function generateReport(type, format) {
  showToast(`Generating ${type} report as ${format}...`, 'success');
}

/* ── MODALS ── */
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

/* ── TOAST ── */
function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  const icons = { success: 'fa-check-circle', danger: 'fa-times-circle', warning: 'fa-exclamation-circle' };
  document.getElementById('toastIcon').className = `fas ${icons[type] || icons.success}`;
  toast.className = `toast ${type} show`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 3500);
}
