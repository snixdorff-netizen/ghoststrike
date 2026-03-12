# Deployment Notes

## Container Demo

1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://127.0.0.1:8000`.

The compose stack starts both the API and a dedicated worker process. The service will create `./data/ada_iq.db` and seed demo projects on first startup when the database is empty.

## Environment Variables

- `ADA_IQ_DB_PATH`: path to the SQLite database file
- `ADA_IQ_SEED_PATH`: path to the demo project seed file
- `ADA_IQ_AUTO_SEED`: whether startup should seed demo projects into an empty database
- `ADA_IQ_OPEN_REGISTRATION`: whether public signup is enabled; keep this `false` for alpha sharing
- `ADA_IQ_BUILD_LABEL`: label shown in the live UI for the current deployed build
- `ADA_IQ_ENABLE_DEMO_ACCOUNT`: whether the demo login should be created and shown in the UI
- `ADA_IQ_DEMO_ACCOUNT_EMAIL`: demo login email
- `ADA_IQ_DEMO_ACCOUNT_PASSWORD`: demo login password
- `ADA_IQ_BOOTSTRAP_ADMIN_EMAIL`: admin account email created automatically on first boot
- `ADA_IQ_BOOTSTRAP_ADMIN_PASSWORD`: admin account password created automatically on first boot
- `ADA_IQ_PORT`: HTTP port for local or containerized startup

## Partner Review Notes

- The Docker image installs only the app package and its runtime dependencies.
- Static UI assets are packaged into the Python distribution.
- Demo data is deterministic, so reviewers should see the same initial project set on a clean database.
