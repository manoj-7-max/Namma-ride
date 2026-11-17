# Private pilot setup

1. Deploy PostgreSQL and the FastAPI service behind HTTPS; never expose PostgreSQL publicly.
2. Generate unique database, admin, JWT and OTP secrets. Keep `EXPOSE_TEST_OTP=false` unless a supervised test explicitly requires it.
3. Restrict CORS to the Admin origin and restrict access at the network/identity layer.
4. Configure matching radius, fix age/accuracy, update interval and offer timeout for Madurantakam.
5. Approve only the ten verified pilot drivers.
6. Set GitHub repository variable `PILOT_API_BASE_URL` to the HTTPS API and run the APK workflow.
7. Install artifacts on test phones, grant foreground location only, and verify the Driver app stops updates when offline/closed.
8. Test no-driver, rejection/timeout retry, cancellation, GPS-off, denial, offline/reconnect and lifecycle flows before supervised rides.

## Operational limitations

The public OpenStreetMap tile servers require attribution and compliance with their tile policy. They offer no unlimited-use guarantee or routing. A commercial tile/routing provider requires separate credentials, pricing review and terms; store any future key in CI/deployment secrets, not source.

The API has no always-running dispatch worker: offer expiry/retry occurs when an authorized app polls or fetches requests. This is suitable for the small supervised pilot, not high-volume public dispatch. SSE gives low-latency events while connected; clients reconcile by polling after reconnect.

No background Android location, payment, public availability, emergency response, production signing or legal/compliance certification is provided.

