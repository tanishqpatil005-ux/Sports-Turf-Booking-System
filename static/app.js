const $ = (s) => document.querySelector(s);
let playersCache = [], bookingsCache = [];
let selectedFacilityId = 0;
const money = n => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
const niceDate = d => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', weekday: 'short' });
async function api(path, options = {}) {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await res.json().catch(() => ({ detail: 'Unexpected server response' }));
  if (!res.ok) {
    let msg = 'Request failed';
    if (typeof data.detail === 'string') msg = data.detail;
    else if (Array.isArray(data.detail)) msg = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
    else if (data.detail) msg = JSON.stringify(data.detail);
    throw new Error(msg);
  }
  return data;
}
let toastTimer;
function toast(msg) { const el = $('#toast'); el.textContent = msg; el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3500) }
function modal(id, show = true) { $('#' + id).classList.toggle('show', show) }
document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => modal(b.dataset.close, false)));
document.querySelectorAll('.modal-backdrop').forEach(b => b.addEventListener('click', e => { if (e.target === b) b.classList.remove('show') }));
$('#openProfile').addEventListener('click', () => modal('profileModal'));
$('#openGameModal').addEventListener('click', async () => { await loadPlayers(); await loadBookings(); modal('gameModal') });
$('#searchButton').addEventListener('click', loadFacilities);
$('#searchInput').addEventListener('keydown', e => { if (e.key === 'Enter') loadFacilities() });
$('#sportFilter').addEventListener('change', loadFacilities);
$('#dateFilter').addEventListener('change', () => loadSlots());
document.querySelectorAll('a[href="#slots"]').forEach(a => a.addEventListener('click', () => { selectedFacilityId = 0; loadSlots(0) }));
async function loadStats() { try { const s = await api('/api/stats'); $('#statFacilities').textContent = s.facilities; $('#statSlots').textContent = s.available_slots; $('#statPlayers').textContent = s.players; $('#statGames').textContent = s.open_games } catch (e) { toast(e.message) } }
async function loadFacilities() {
  const grid = $('#facilityGrid'); grid.innerHTML = '<div class="loading-card">Finding your next playground…</div>';
  try {
    const p = new URLSearchParams({ q: $('#searchInput').value.trim(), sport: $('#sportFilter').value });
    const list = await api('/api/facilities?' + p);
    if (!list.length) { grid.innerHTML = '<div class="empty-state">No facilities match those filters. Try another search.</div>'; return }
    grid.innerHTML = list.map(f => `<article class="facility-card"><div class="facility-image"><span class="sport-pill">${escapeHtml(f.sport_type)}</span></div><div class="facility-body"><div class="facility-title"><div><h3>${escapeHtml(f.facility_name)}</h3><div class="facility-location">⌖ ${escapeHtml(f.address)}</div></div><strong>${money(f.price)}<small> / slot</small></strong></div><div class="facility-meta"><span>◷ ${f.available_slots} upcoming slots</span><button class="mini-link" data-facility="${f.facility_id}">View slots ↗</button></div></div></article>`).join('');
    grid.querySelectorAll('[data-facility]').forEach(b => b.addEventListener('click', () => { selectedFacilityId = Number(b.dataset.facility); loadSlots(selectedFacilityId); document.querySelector('#slots').scrollIntoView({ behavior: 'smooth' }) }));
  } catch (e) { grid.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}. Is the backend running?</div>` }
}
async function loadSlots(facilityId = selectedFacilityId) {
  if (typeof facilityId === 'number') selectedFacilityId = facilityId;
  const subtitle = document.querySelector('.panel-title p');
  if (subtitle) {
    if (selectedFacilityId) {
      subtitle.innerHTML = 'Showing slots for selected turf · <button class="mini-link" id="clearTurfFilter" type="button" style="background:none;border:0;color:var(--forest);font-weight:700;padding:0;cursor:pointer;">Show all turfs</button>';
      document.querySelector('#clearTurfFilter')?.addEventListener('click', () => { selectedFacilityId = 0; loadSlots(0) });
    } else {
      subtitle.textContent = 'Upcoming availability';
    }
  }
  const list = $('#slotList'); list.innerHTML = '<div class="empty-state">Loading slots…</div>';
  try {
    const p = new URLSearchParams(); if (selectedFacilityId) p.set('facility_id', selectedFacilityId); if ($('#dateFilter').value) p.set('slot_date', $('#dateFilter').value);
    const slots = await api('/api/slots?' + p);
    if (!slots.length) { list.innerHTML = '<div class="empty-state">No available slots for this date. Choose another date or turf.</div>'; return }
    list.innerHTML = slots.map(s => `<div class="slot-row"><div><b>${escapeHtml(s.facility_name)}</b><small>${niceDate(s.slot_date)} · ${s.start_time}–${s.end_time}</small></div><div><b>${escapeHtml(s.sport_type)}</b><small>${escapeHtml(s.address)}</small></div><div class="slot-price">${money(s.price)}</div><button class="btn btn-lime" data-book="${s.slot_id}">Book ↗</button></div>`).join('');
    list.querySelectorAll('[data-book]').forEach(b => b.addEventListener('click', () => bookSlot(Number(b.dataset.book))));
  } catch (e) { list.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>` }
}
async function loadPlayers() {
  try { playersCache = await api('/api/players'); const sel = $('#hostPlayer'); sel.innerHTML = playersCache.map(p => `<option value="${p.player_id}">${escapeHtml(p.player_name)} · ${escapeHtml(p.skill_level)}</option>`).join(''); if (!playersCache.length) sel.innerHTML = '<option value="">Create a profile first</option>' }
  catch (e) { toast(e.message) }
}
async function bookSlot(slotId) {
  try {
    if (!playersCache.length) playersCache = await api('/api/players');
    if (!playersCache.length) { toast('Create a player profile first, then book your slot.'); modal('profileModal'); return }
    const choices = playersCache.map(p => `${p.player_id}: ${p.player_name}`).join('\n');
    const choice = prompt('Book as which player? Enter the player ID:\n' + choices, String(playersCache[0].player_id));
    if (choice === null) return;
    const playerId = Number(choice);
    if (!playersCache.some(p => p.player_id === playerId)) { toast('That player ID is not in the list.'); return }
    const result = await api('/api/bookings', { method: 'POST', body: JSON.stringify({ player_id: playerId, slot_id: slotId }) });
    toast(`Booking #${result.booking_id} confirmed · ${money(result.payment_amount)}. Demo only, no payment taken.`);
    await Promise.all([loadSlots(selectedFacilityId), loadStats(), loadBookings()]);
  } catch (e) { toast(e.message); loadSlots(selectedFacilityId) }
}
async function loadBookings() {
  try {
    bookingsCache = await api('/api/bookings');
    const sel = $('#hostBooking');
    sel.innerHTML = bookingsCache.map(b => `<option value="${b.booking_id}">#${b.booking_id} · ${escapeHtml(b.facility_name)} · ${b.slot_date} · ${escapeHtml(b.player_name)}</option>`).join('');
    if (!bookingsCache.length) sel.innerHTML = '<option value="">No bookings yet. Book a slot first.</option>';
  } catch (e) { toast(e.message) }
}
async function loadGames() {
  const grid = $('#gamesGrid');
  try {
    const games = await api('/api/games');
    if (!games.length) { grid.innerHTML = '<div class="empty-state">No open games yet. Book a slot, then choose “Host a game” to create the first one.</div>'; return }
    grid.innerHTML = games.map(g => `<article class="game-card"><div class="game-top"><span class="game-sport">${escapeHtml(g.sport_type.toUpperCase())}</span><span class="open-pill">● OPEN</span></div><h3>${escapeHtml(g.facility_name)}</h3><div class="game-location">⌖ ${escapeHtml(g.address)}</div><div class="game-details"><span>◷ ${niceDate(g.slot_date)} · ${g.start_time}</span><span>♙ ${g.joined_count}/${g.roster_size} players</span></div><div class="game-bottom"><small>Hosted by ${escapeHtml(g.host_name)}<br>Skill: ${escapeHtml(g.minimum_skill_level)}</small><button class="btn btn-dark" data-join="${g.game_id}">Join game ↗</button></div></article>`).join('');
    grid.querySelectorAll('[data-join]').forEach(b => b.addEventListener('click', () => joinGame(Number(b.dataset.join))));
  } catch (e) { grid.innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>` }
}
async function joinGame(gameId) {
  try {
    if (!playersCache.length) playersCache = await api('/api/players');
    if (!playersCache.length) { toast('Create a player profile first.'); modal('profileModal'); return }
    const choice = prompt('Enter your player ID:\n' + playersCache.map(p => `${p.player_id}: ${p.player_name}`).join('\n'), String(playersCache[0].player_id));
    if (choice === null) return;
    const playerId = Number(choice);
    if (!playersCache.some(p => p.player_id === playerId)) { toast('That player ID is not in the list.'); return }
    const result = await api(`/api/games/${gameId}/join`, { method: 'POST', body: JSON.stringify({ player_id: playerId }) });
    toast(result.message); await Promise.all([loadGames(), loadStats()]);
  } catch (e) { toast(e.message); loadGames() }
}
$('#profileForm').addEventListener('submit', async e => {
  e.preventDefault(); const data = Object.fromEntries(new FormData(e.target).entries());
  try { const player = await api('/api/players', { method: 'POST', body: JSON.stringify(data) }); toast(`Profile created for ${player.player_name} · Player ID ${player.player_id}`); e.target.reset(); modal('profileModal', false); await Promise.all([loadPlayers(), loadStats()]) }
  catch (err) { toast(err.message) }
});
$('#gameForm').addEventListener('submit', async e => {
  e.preventDefault(); const d = Object.fromEntries(new FormData(e.target).entries());
  d.host_player_id = Number(d.host_player_id); d.booking_id = Number(d.booking_id); d.roster_size = Number(d.roster_size);
  try { const result = await api('/api/games', { method: 'POST', body: JSON.stringify(d) }); toast(result.message); modal('gameModal', false); await Promise.all([loadGames(), loadStats()]) }
  catch (err) { toast(err.message) }
});
function escapeHtml(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])) }
async function init() {
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  const y = tomorrow.getFullYear(), m = String(tomorrow.getMonth() + 1).padStart(2, '0'), d = String(tomorrow.getDate()).padStart(2, '0');
  $('#dateFilter').min = `${y}-${m}-${d}`;
  await Promise.all([loadStats(), loadFacilities(), loadSlots(), loadPlayers(), loadGames(), loadBookings()])
}
init();
