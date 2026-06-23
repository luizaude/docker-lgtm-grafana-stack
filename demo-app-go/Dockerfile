FROM golang:1.24-alpine AS builder

WORKDIR /app
RUN apk add --no-cache ca-certificates

# Copy module files first to leverage layer caching
COPY go.mod go.sum ./
RUN go mod download

# Then copy source code and build
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server .

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=builder /server /server

ENV PORT=8081
EXPOSE 8081

USER nobody
ENTRYPOINT ["/server"]