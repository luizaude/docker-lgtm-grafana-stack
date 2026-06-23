package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

func main() {
	ctx := context.Background()

	endpoint := strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
	if endpoint == "" {
		endpoint = "localhost:4317"
	}
	endpoint = strings.TrimPrefix(endpoint, "http://")
	endpoint = strings.TrimPrefix(endpoint, "https://")

	serviceName := strings.TrimSpace(os.Getenv("OTEL_SERVICE_NAME"))
	if serviceName == "" {
		serviceName = "demo-app-go"
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(
			attribute.String("service.name", serviceName),
			attribute.String("service.version", "1.0.0"),
			attribute.String("deployment.environment", "development"),
		),
	)
	if err != nil {
		log.Fatalf("resource: %v", err)
	}

	traceExporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithInsecure(),
		otlptracegrpc.WithEndpoint(endpoint),
	)
	if err != nil {
		log.Fatalf("otlp trace exporter: %v", err)
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(traceExporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	defer func() { _ = tp.Shutdown(context.Background()) }()

	metricExporter, err := otlpmetricgrpc.New(ctx,
		otlpmetricgrpc.WithInsecure(),
		otlpmetricgrpc.WithEndpoint(endpoint),
	)
	if err != nil {
		log.Fatalf("otlp metric exporter: %v", err)
	}

	mp := sdkmetric.NewMeterProvider(
		sdkmetric.WithReader(sdkmetric.NewPeriodicReader(metricExporter, sdkmetric.WithInterval(5*time.Second))),
		sdkmetric.WithResource(res),
	)
	otel.SetMeterProvider(mp)
	defer func() { _ = mp.Shutdown(context.Background()) }()

	m := otel.Meter("demo-app-go")
	requestCounter, err := m.Int64Counter("app_requests_total",
		metric.WithDescription("Total HTTP requests"),
	)
	if err != nil {
		log.Fatalf("counter: %v", err)
	}

	mux := http.NewServeMux()
	tr := otel.Tracer("demo-app-go")

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		requestCounter.Add(r.Context(), 1, metric.WithAttributes(attribute.String("path", "/")))
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"message":   "demo-app-go (OpenTelemetry)",
			"service":   serviceName,
			"endpoints": []string{"/", "/api/work"},
		})
	})

	mux.HandleFunc("/api/work", func(w http.ResponseWriter, r *http.Request) {
		requestCounter.Add(r.Context(), 1, metric.WithAttributes(attribute.String("path", "/api/work")))
		if err := doWork(r.Context(), tr); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	handler := otelhttp.NewHandler(mux, "demo-app-go",
		otelhttp.WithSpanNameFormatter(func(operation string, r *http.Request) string {
			return fmt.Sprintf("%s %s", r.Method, r.URL.Path)
		}),
	)

	addr := ":8081"
	if p := strings.TrimSpace(os.Getenv("PORT")); p != "" {
		if strings.HasPrefix(p, ":") {
			addr = p
		} else {
			addr = ":" + p
		}
	}

	log.Printf("listening on %s, OTLP endpoint %s, service %s", addr, endpoint, serviceName)
	if err := http.ListenAndServe(addr, handler); err != nil {
		log.Fatal(err)
	}
}

func doWork(ctx context.Context, tr trace.Tracer) error {
	_, sp := tr.Start(ctx, "simulate-internal")
	defer sp.End()
	time.Sleep(50 * time.Millisecond)
	_, sp2 := tr.Start(ctx, "nested-step")
	defer sp2.End()
	time.Sleep(25 * time.Millisecond)
	return nil
}
