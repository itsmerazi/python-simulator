# python-simulator

> **The goal: tap a button on your phone, and a moment later a robot moves on a web page that anyone in the world can watch.**

That is how smart home gadgets, delivery robots and factory machines are run today: commands travel over the internet to a "brain" in the cloud, and the result travels back. This repo is that brain: the **Python engine** of a larger project, an *AWS IoT Robot Simulation* built on AWS IoT Core. The robot is simulated, so no hardware is needed.

## Why it's interesting

- **Never gets mixed up.** Many phones can drive at once, and each one gets confirmation only for its own commands.
- **Only trusted devices get in.** Every phone, server and browser has to prove who it is before it can send or watch anything.
- **Stays safe when things go wrong.** A slow connection never freezes the robot, a repeated message is never applied twice, and the robot stops by itself if the phone goes quiet for one second.

| Part | Runs on | Status |
| --- | --- | --- |
| Python engine (this repo) | EC2, Docker | Done, running continuously |
| AWS IoT Core | AWS | Configured |
| React dashboard | S3 + CloudFront | In development (separate repo) |
| Android controller | Phone / emulator | In development (separate repo) |

## How it works

Controller → `simulation/commands/<clientId>` → engine → `simulation/audit/<clientId>` (sender only) and `simulation/telemetry` (all viewers).

- Fixed 60 Hz physics, telemetry capped at 30 messages/s and sent only when the robot moves.
- Client identity is read from the MQTT topic, never from the message body.
- Duplicates are detected by `(client_id, correlation_id)` with a 60 s TTL and answered as `duplicate`.
- Two bounded queues (inbound and outbound) so the loop never blocks.
- Simple two-wheel robot, no clock or randomness, so runs are replayable from the logs.

Example command:

```json
{ "schema_version": 1,
  "correlation_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "payload": { "control": "throttle", "value": 0.65 } }
```

## Run it

Needs Python 3.12, an AWS IoT endpoint and an engine certificate.

```bash
git clone https://github.com/itsmerazi/python-simulator.git
cd python-simulator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                 # tests need no AWS

export IOT_ENDPOINT=<endpoint> CLIENT_ID=ssot-engine
export CERT_PATH=certs/engine.cert.pem KEY_PATH=certs/engine.private.key CA_PATH=certs/AmazonRootCA1.pem
python -m engine.main
```

Docker: `docker build -t ssot-engine .`, then run it with the same variables and your `certs/` folder mounted read-only.

## Layout

`engine/` holds config, logging, messages, queues, MQTT I/O, simulation core, protocol and `main.py`. `tests/` has one test file per module.

## Security

Certificates and `local.env` are git-ignored. Never commit keys.

## Status and next steps

This repo is the engine, and it is complete and running continuously on EC2. The React dashboard (S3 + CloudFront) and the Android controller are developed in separate repositories and will be linked here once they are public. End-to-end latency measurements will follow.

Questions, ideas and feedback are welcome. Feel free to open an issue.
