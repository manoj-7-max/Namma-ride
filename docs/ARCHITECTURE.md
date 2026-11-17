# Phase 3 architecture

Flutter Customer / Flutter Driver / React Admin → FastAPI → PostgreSQL 16.

## Location and matching

`driver_locations` contains exactly one replaceable fix per approved driver: coordinates, accuracy, capture/update time and availability. The API rejects invalid ranges, future/stale fixes, poor accuracy and updates faster than the configured limit. Identity always comes from the verified driver JWT.

For the 10-driver pilot, FastAPI computes Haversine distance over recent, accurate, available rows. It persists only the selected offer in `ride_dispatches`. A PostgreSQL `SELECT ... FOR UPDATE` lock serializes acceptance; the ride's terminal assignment check prevents double claims. Offers have deadlines. Poll/read operations expire overdue offers and select the next nearest untried driver; exhaustion becomes `no_driver_available`, and the customer can request a rematch.

## Live events and privacy

`ride_events` stores lifecycle/dispatch facts, not continuous coordinates. Authorized users can consume bearer-protected SSE at `/api/v1/rides/{id}/events/stream` or poll `/events?after_id=`. Clients reconnect by retaining the last event ID and always reconcile with the ride endpoint.

A customer receives driver coordinates only after assignment while status is accepted, arrived or started. Other customers and unassigned drivers are denied. Admin operations intentionally expose online state and timestamps but not coordinates or customer personal data.

## Maps

The Customer app uses `flutter_map` and OpenStreetMap tiles with attribution. This avoids embedding a map key for the private pilot, but public OSM tiles have a usage policy and are not unlimited. Navigation is handed to an installed Android app. ETA is labeled estimated and uses straight-line distance, not a routing API.

## Runtime boundaries

Android requests fine/coarse foreground location only. The Driver app sends fixes while visibly online and active; it has no background-location permission. Payments/public operations remain disabled and Bike Taxi is demo-only.
