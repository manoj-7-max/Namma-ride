import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Summary = { customers: number; drivers: number; pending_drivers: number; rides: number; online_drivers: number; active_rides: number; customer_limit: number; driver_limit: number };
type Driver = { id: number; display_name: string; phone: string; vehicle_number: string | null; approved: boolean; suspended: boolean };
type Customer = { id: number; display_name: string; phone: string; active: boolean; created_at: string };
type Audit = { id: number; action: string; target_type: string; target_id: number | null; detail: string | null; created_at: string };
type Ride = { id: number; pickup: string; dropoff: string; status: string; estimated_fare_rupees: number; driver: Driver | null };
type Operations = {
  drivers: { id: number; display_name: string; vehicle_number: string | null; approved: boolean; available: boolean; last_location_at: string | null }[];
  active_rides: { id: number; status: string; driver_id: number | null; updated_at: string }[];
  failures: { ride_id: number; type: string; created_at: string }[];
};
const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

function App() {
  const [key, setKey] = useState('');
  const [token, setToken] = useState('');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [rides, setRides] = useState<Ride[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [operations, setOperations] = useState<Operations | null>(null);
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
    const [nextSummary, nextDrivers, nextRides, nextOperations, nextCustomers, nextAudit] = await Promise.all([
      request<Summary>('/api/v1/admin/summary', {}, authToken),
      request<Driver[]>('/api/v1/admin/drivers', {}, authToken),
      request<Ride[]>('/api/v1/admin/rides', {}, authToken),
      request<Operations>('/api/v1/admin/operations', {}, authToken),
      request<Customer[]>('/api/v1/admin/customers', {}, authToken),
      request<Audit[]>('/api/v1/admin/audit', {}, authToken),
    ]);
    setSummary(nextSummary); setDrivers(nextDrivers); setRides(nextRides); setOperations(nextOperations); setCustomers(nextCustomers); setAudit(nextAudit);
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

  async function suspend(driver: Driver, suspended: boolean) {
    setBusy(true); setError('');
    try { await request(`/api/v1/admin/drivers/${driver.id}/suspension`, { method: 'PATCH', body: JSON.stringify({ suspended }) }); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Update failed'); }
    finally { setBusy(false); }
  }

  async function setCustomerActive(customer: Customer, active: boolean) {
    setBusy(true); setError('');
    try { await request(`/api/v1/admin/customers/${customer.id}/active`, { method: 'PATCH', body: JSON.stringify({ active }) }); await load(); }
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
    <small>PRIVATE TEST · PHASE 3</small><h1>Namma Ride Live Operations</h1>
    <p>Madurantakam, Tamil Nadu · Bike Taxi demo-only · No payments</p>
    {!token && <form onSubmit={login}><label htmlFor="key">Admin API key</label><input id="key" type="password" autoComplete="off" required value={key} onChange={e => setKey(e.target.value)} /><button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form>}
    {error && <p role="alert">{error}</p>}
    {summary && <>
      <section className="metrics"><article><h2>{summary.customers}/{summary.customer_limit}</h2>Customers</article><article><h2>{summary.drivers}/{summary.driver_limit}</h2>Drivers</article><article><h2>{summary.pending_drivers}</h2>Pending approval</article><article><h2>{summary.rides}</h2>Rides</article></section>
      <section className="metrics"><article><h2>{summary.online_drivers}</h2>Online drivers</article><article><h2>{summary.active_rides}</h2>Active rides</article></section>
      <div className="toolbar"><button disabled={busy} onClick={() => load().catch(e => setError(String(e)))}>Refresh</button></div>
      <h2>Drivers</h2><div className="table"><table><thead><tr><th>Name</th><th>Phone</th><th>Vehicle</th><th>Status</th><th>Actions</th></tr></thead><tbody>{drivers.map(driver => <tr key={driver.id}><td>{driver.display_name}</td><td>{driver.phone}</td><td>{driver.vehicle_number || '—'}</td><td>{driver.suspended ? 'Suspended' : driver.approved ? 'Approved' : 'Pending'}</td><td><button disabled={busy} onClick={() => approve(driver, !driver.approved)}>{driver.approved ? 'Revoke' : 'Approve'}</button> <button disabled={busy} onClick={() => suspend(driver, !driver.suspended)}>{driver.suspended ? 'Restore' : 'Suspend'}</button></td></tr>)}</tbody></table></div>
      <h2>Customers</h2><div className="table"><table><thead><tr><th>Name</th><th>Phone</th><th>Joined</th><th>Status</th><th>Action</th></tr></thead><tbody>{customers.map(customer => <tr key={customer.id}><td>{customer.display_name}</td><td>{customer.phone}</td><td>{new Date(customer.created_at).toLocaleDateString()}</td><td>{customer.active ? 'Active' : 'Inactive'}</td><td><button disabled={busy} onClick={() => setCustomerActive(customer, !customer.active)}>{customer.active ? 'Deactivate' : 'Activate'}</button></td></tr>)}</tbody></table></div>
      <h2>Rides</h2><div className="table"><table><thead><tr><th>ID</th><th>Route</th><th>Driver</th><th>Demo fare</th><th>Status</th><th>Action</th></tr></thead><tbody>{rides.map(ride => <tr key={ride.id}><td>#{ride.id}</td><td>{ride.pickup} → {ride.dropoff}</td><td>{ride.driver?.display_name || 'Unassigned'}</td><td>₹{ride.estimated_fare_rupees}</td><td>{ride.status}</td><td>{!['completed', 'cancelled'].includes(ride.status) && <button disabled={busy} onClick={() => cancelRide(ride)}>Cancel</button>}</td></tr>)}</tbody></table></div>
      {operations && <><h2>Driver connectivity</h2><div className="table"><table><thead><tr><th>Driver</th><th>Vehicle</th><th>State</th><th>Last update</th></tr></thead><tbody>{operations.drivers.map(driver => <tr key={driver.id}><td>{driver.display_name}</td><td>{driver.vehicle_number || '—'}</td><td>{driver.available ? 'Online' : 'Offline'}</td><td>{driver.last_location_at ? new Date(driver.last_location_at).toLocaleString() : 'Never'}</td></tr>)}</tbody></table></div><h2>Recent matching failures</h2>{operations.failures.length === 0 ? <p>None recorded.</p> : <ul>{operations.failures.map((failure, index) => <li key={`${failure.ride_id}-${index}`}>Ride #{failure.ride_id}: {failure.type} · {new Date(failure.created_at).toLocaleString()}</li>)}</ul>}</>}
      <h2>Admin audit</h2>{audit.length === 0 ? <p>No admin changes recorded.</p> : <div className="table"><table><thead><tr><th>Time</th><th>Action</th><th>Target</th><th>Value</th></tr></thead><tbody>{audit.map(entry => <tr key={entry.id}><td>{new Date(entry.created_at).toLocaleString()}</td><td>{entry.action}</td><td>{entry.target_type} #{entry.target_id ?? '—'}</td><td>{entry.detail ?? '—'}</td></tr>)}</tbody></table></div>}
    </>}
    <p className="note">Private testing only. No public ride operations or real payment processing.</p>
  </main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
