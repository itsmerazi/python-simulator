import queue
import time
from awscrt import mqtt
from awsiot import mqtt_connection_builder
from .jsonlog import log
from .queues import put_wait

def connect(s):
    def on_interrupted(connection, error, **kwargs):
        log("mqtt_interrupted", error=str(error))
    def on_resumed(connection, return_code, session_present, **kwargs):
        log("mqtt_resumed", code=str(return_code), session_present=session_present)
        if not session_present:
            connection.resubscribe_existing_topics()

    conn = mqtt_connection_builder.mtls_from_path(
    endpoint=s.iot_endpoint,
    cert_filepath=s.cert_path,
    pri_key_filepath=s.key_path,
    ca_filepath=s.ca_path,
    client_id=s.client_id,
    clean_session=True,
    keep_alive_secs=30,
    on_connection_interrupted=on_interrupted,
    on_connection_resumed=on_resumed,
    )
    conn.connect().result()
    log("mqtt_connected", client_id=s.client_id)
    return conn

def subscribe_commands(conn, q1):
    def on_message(topic, payload, dup, qos, retain, **kwargs):
        client_id = topic.rsplit("/", 1)[-1] # identity comes from the topic
        if not put_wait(q1, (client_id, payload, time.monotonic()), 0.05):
            log("q1_full_dropped", client_id=client_id)

    future, _ = conn.subscribe(topic="simulation/commands/+",
    qos=mqtt.QoS.AT_LEAST_ONCE, callback=on_message)
    future.result()
    log("subscribed", topic="simulation/commands/+")

def egress_loop(conn, q2, stop):
    while not stop.is_set():
        try:
            topic, payload, qos = q2.get(timeout=0.5)
        except queue.Empty:
            continue
        mode = mqtt.QoS.AT_LEAST_ONCE if qos == 1 else mqtt.QoS.AT_MOST_ONCE
        future, _ = conn.publish(topic=topic, payload=payload, qos=mode)
        future.add_done_callback(lambda f, t=topic: _failed(f, t))

def _failed(future, topic):
    error = future.exception()
    if error:
        log("publish_failed", topic=topic, error=str(error))