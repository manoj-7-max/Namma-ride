import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Summary = {
  customers: number;
  drivers: number;
  customer_limit: number;
  driver_limit: number;
};

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

function App() {
  const [key, setKey] = useState('');
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function load(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setData(null);
    try {
      const response = await fetch(`${apiBase}/api/v1/admin/summary`, {
        headers: { 'X-Admin-Key': key },
        signal: AbortSignal.timeout(10_000),
      });
      if (!response.ok) {
        throw new Error(response.status === 401
          ? 'Check your admin key.'
          : 'API unavailable. Check the backend and database.');
      }
      setData(await response.json() as Summary);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to connect');
    } finally {
      setBusy(false);
    }
  }

  return <main>
    <small>PRIVATE PILOT · PHASE 1</small>
    <h1>Namma Ride</h1>
    <p>Madurantakam, Tamil Nadu · Private test dashboard</p>
    <form onSubmit={load}>
      <label htmlFor="key">Local admin API key</label>
      <input id="key" type="password" autoComplete="off" required
        value={key} onChange={e => setKey(e.target.value)} />
      <button disabled={busy}>{busy ? 'Loading…' : 'Load pilot summary'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {data && <section aria-live="polite">
      <article><h2>{data.customers} / {data.customer_limit}</h2>Customers</article>
      <article><h2>{data.drivers} / {data.driver_limit}</h2>Drivers</article>
    </section>}
    <p className="note">
      Bike Taxi is demo-only. No public ride operations or real payments.
      This Phase 1 dashboard shows pilot enrollment counts;
      onboarding, dispatch and tracking are not enabled.
    </p>
  </main>;
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
