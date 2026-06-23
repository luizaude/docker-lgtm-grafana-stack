"""
Demo Application - Generates logs, metrics and traces
Sends telemetry to Grafana Alloy via OpenTelemetry
"""

import logging
import random
import time
from flask import Flask, jsonify

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
import os

# Configuration
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "demo-app")

# Resource
resource = Resource.create({
    "service.name": SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

# Setup Tracing
trace_provider = TracerProvider(resource=resource)
trace_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# Setup Metrics
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
    export_interval_millis=5000
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Setup Logging
logger_provider = LoggerProvider(resource=resource)
log_exporter = OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# Create custom metrics
request_counter = meter.create_counter(
    name="app_requests_total",
    description="Total number of requests",
    unit="1"
)

request_duration = meter.create_histogram(
    name="app_request_duration_seconds",
    description="Request duration in seconds",
    unit="s"
)

active_users = meter.create_up_down_counter(
    name="app_active_users",
    description="Number of active users",
    unit="1"
)

# Flask App
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


@app.route("/")
def home():
    """Home endpoint"""
    logging.info("Home endpoint called")
    request_counter.add(1, {"endpoint": "/", "method": "GET"})
    return jsonify({
        "message": "Welcome to the Demo App!",
        "service": SERVICE_NAME,
        "endpoints": ["/", "/api/users", "/api/orders", "/api/slow", "/api/error"]
    })


@app.route("/api/users")
def get_users():
    """Simulates fetching users from database"""
    with tracer.start_as_current_span("fetch-users") as span:
        start_time = time.time()
        
        # Simulate DB query
        with tracer.start_as_current_span("db-query"):
            time.sleep(random.uniform(0.01, 0.1))
            users = [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"}
            ]
        
        # Simulate processing
        with tracer.start_as_current_span("process-data"):
            time.sleep(random.uniform(0.005, 0.02))
        
        duration = time.time() - start_time
        span.set_attribute("users.count", len(users))
        
        request_counter.add(1, {"endpoint": "/api/users", "method": "GET"})
        request_duration.record(duration, {"endpoint": "/api/users"})
        
        logging.info(f"Fetched {len(users)} users in {duration:.3f}s")
        
        return jsonify(users)


@app.route("/api/orders")
def get_orders():
    """Simulates fetching orders with external service call"""
    with tracer.start_as_current_span("fetch-orders") as span:
        start_time = time.time()
        
        # Simulate DB query
        with tracer.start_as_current_span("db-query"):
            time.sleep(random.uniform(0.02, 0.15))
            orders = [
                {"id": 101, "user_id": 1, "total": 99.99},
                {"id": 102, "user_id": 2, "total": 149.50},
            ]
        
        # Simulate external payment service call
        with tracer.start_as_current_span("payment-service-call") as payment_span:
            payment_span.set_attribute("service.name", "payment-service")
            time.sleep(random.uniform(0.05, 0.2))
            payment_span.set_attribute("payment.status", "verified")
        
        duration = time.time() - start_time
        span.set_attribute("orders.count", len(orders))
        
        request_counter.add(1, {"endpoint": "/api/orders", "method": "GET"})
        request_duration.record(duration, {"endpoint": "/api/orders"})
        
        logging.info(f"Fetched {len(orders)} orders in {duration:.3f}s")
        
        return jsonify(orders)


@app.route("/api/slow")
def slow_endpoint():
    """Simulates a slow endpoint for testing"""
    with tracer.start_as_current_span("slow-operation") as span:
        delay = random.uniform(1, 3)
        span.set_attribute("delay.seconds", delay)
        
        logging.warning(f"Slow operation starting, will take {delay:.2f}s")
        time.sleep(delay)
        
        request_counter.add(1, {"endpoint": "/api/slow", "method": "GET"})
        request_duration.record(delay, {"endpoint": "/api/slow"})
        
        logging.info(f"Slow operation completed after {delay:.2f}s")
        
        return jsonify({"message": "Slow operation completed", "delay": delay})


@app.route("/api/error")
def error_endpoint():
    """Simulates an error for testing"""
    with tracer.start_as_current_span("error-operation") as span:
        error_type = random.choice(["timeout", "validation", "not_found"])
        span.set_attribute("error.type", error_type)
        
        logging.error(f"Error occurred: {error_type}")
        request_counter.add(1, {"endpoint": "/api/error", "method": "GET", "status": "error"})
        
        if error_type == "timeout":
            return jsonify({"error": "Request timeout"}), 504
        elif error_type == "validation":
            return jsonify({"error": "Validation failed"}), 400
        else:
            return jsonify({"error": "Resource not found"}), 404


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    logging.info(f"Starting {SERVICE_NAME} on port 8080")
    logging.info(f"Sending telemetry to {OTEL_ENDPOINT}")
    app.run(host="0.0.0.0", port=8080, debug=False)
