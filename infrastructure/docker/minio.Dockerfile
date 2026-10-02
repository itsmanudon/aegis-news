# Build the approved third-party storage service; application code remains Python/TS.
FROM golang:1.24.9-alpine AS build
WORKDIR /src
ADD --checksum=sha256:be6d0bd3696c3a13a35f02d3a0280b64319c67918b4501c5c3d87f96d000085c https://codeload.github.com/minio/minio/tar.gz/refs/tags/RELEASE.2025-10-15T17-29-55Z /tmp/minio.tar.gz
RUN tar -xzf /tmp/minio.tar.gz --strip-components=1 -C /src
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/minio .
FROM alpine:3.22
RUN apk add --no-cache ca-certificates && adduser -D -u 10001 minio && mkdir -p /data && chown minio:minio /data
COPY --from=build /out/minio /usr/local/bin/minio
COPY --from=build /src/LICENSE /usr/share/licenses/minio/LICENSE
USER minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
