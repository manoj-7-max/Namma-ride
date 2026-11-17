import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Summary = { customers: number; drivers: number; pending_drivers: number; rides: number; customer_limit: number; driver_limit: number };
type Driver = { id: number; display_name: string; phone: string; vehicle_number: string | null; approved: boolean };
type Ride = { id: number; pickup: string; dropoff: string; status: string; estimated_fare_rupees: number; driver: Driver | null };
const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

function App() {
  const [key, setKey] = useState('');
  const [token, setToken] = useState('');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [rides, setRides] = useState<Ride[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function request<T>(path: string, options: RequestInit = {}, authToken = token): Promise<T> {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (authToken) headers.set('Authorization', `Bearer ${authToken}`);
    const response = await fetch(`${apiBase}${path}`, { ...options, headers, signal: AbortSignal.timeout(10_000) });
    const body = response.status === 204 ? null : await response.json();
    if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
    return body as T;
  }

  async function load(authToken = token) {
    const [nextSummary, nextDrivers, nextRides] = await Promise.all([
      request<Summary>('/api/v1/admin/summary', {}, authToken),
      request<Driver[]>('/api/v1/admin/drivers', {}, authToken),
      request<Ride[]>('/api/v1/admin/rides', {}, authToken),
    ]);
    setSummary(nextSummary); setDrivers(nextDrivers); setRides(nextRides);
  }

  async function login(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await request<{ access_token: string }>('/api/v1/auth/admin-token', { method: 'POST', headers: { 'X-Admin-Key': key } }, '');
      setToken(result.access_token); await load(result.access_token);
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to connect'); }
    finally { setBusy(false); }
  }

  async function approve(driver: Driver, approved: boolean) {
    setBusy(true); setError('');
    try { await request(`/api/v1/admin/drivers/${driver.id}/approval`, { method: 'PATCH', body: JSON.stringify({ approved }) }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Update failed'); }
    finally { setBusy(false); }
  }

  async function cancelRide(ride: Ride) {
    setBusy(true); setError('');
    try { await request(`/api/v1/rides/${ride.id}/status`, { method: 'PATCH', body: JSON.stringify({ status: 'cancelled', cancellation_reason: 'Cancelled by private-test admin' }) }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Cancellation failed'); }
    finally { setBusy(false); }
  }

  return <main>
    <small>PRIVATE TEST · PHASE 2</small><h1>Namma Ride Admin</h1>
    <p>Madurantakam, Tamil Nadu · Bike Taxi demo-only · No payments</p>
    {!token && <form onSubmit={login}><label htmlFor="key">Admin API key</label><input id="key" type="password" autoComplete="off" required value={key} onChange={e => setKey(e.target.value)} /><button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form>}
    {error && <p role="alert">{error}</p>}
    {summary && <>
      <section className="metrics"><article><h2>{summary.customers}/{summary.customer_limit}</h2>Customers</article><article><h2>{summary.drivers}/{summary.driver_limit}</h2>Drivers</article><article><h2>{summary.pending_drivers}</h2>Pending approval</article><article><h2>{summary.rides}</h2>Rides</article></section>
      <div className="toolbar"><button disabled={busy} onClick={() => load().catch(e => setError(String(e)))}>Refresh</button></div>
      <h2>Drivers</h2><div className="table"><table><thead><tr><th>Name</th><th>Phone</th><th>Vehicle</th><th>Status</th><th>Action</th></tr></thead><tbody>{drivers.map(driver => <tr key={driver.id}><td>{driver.display_name}</td><td>{driver.phone}</td><td>{driver.vehicle_number || '—'}</td><td>{driver.approved ? 'Approved' : 'Pending'}</td><td><button disabled={busy} onClick={() => approve(driver, !driver.approved)}>{driver.approved ? 'Revoke' : 'Approve'}</button></td></tr>)}</tbody></table></div>
      <h2>Rides</h2><div className="table"><table><thead><tr><th>ID</th><th>Route</th><th>Driver</th><th>Demo fare</th><th>Status</th><th>Action</th></tr></thead><tbody>{rides.map(ride => <tr key={ride.id}><td>#{ride.id}</td><td>{ride.pickup} → {ride.dropoff}</td><td>{ride.driver?.display_name || 'Unassigned'}</td><td>₹{ride.estimated_fare_rupees}</td><td>{ride.status}</td><td>{!['completed', 'cancelled'].includes(ride.status) && <button disabled={busy} onClick={() => cancelRide(ride)}>Cancel</button>}</td></tr>)}</tbody></table></div>
    </>}
    <p className="note">Private testing only. No public ride operations or real payment processing.</p>
  </main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
