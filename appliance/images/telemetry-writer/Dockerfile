# MQTT → postgres-timeseries bridge for the EMS stack.
#
# Why this exists as an image (not python:3.13-alpine + runtime pip):
# the appliance is airgapped after provisioning. A `pip install` at
# every container restart would 404 the first time the box reboots
# offline → telemetry-writer restart-loops → ingest dies. Baking the
# deps into the image makes the container immutable + restart-clean.

FROM python:3.13-alpine

# Pinned versions — paho-mqtt 2.x is required (script uses
# CallbackAPIVersion.VERSION2). psycopg2-binary 2.9.x is the current
# stable for postgres 15/16.
RUN pip install --no-cache-dir \
    paho-mqtt==2.1.0 \
    psycopg2-binary==2.9.10

WORKDIR /app
COPY telemetry_writer.py /app/telemetry_writer.py

CMD ["python", "/app/telemetry_writer.py"]
