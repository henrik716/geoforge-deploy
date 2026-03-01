FROM geopython/pygeoapi:latest

# Copy configuration
COPY pygeoapi-config.yml /pygeoapi/local.config.yml
COPY data/ /data/

# Generate OpenAPI + AsyncAPI documents at build time
RUN pygeoapi openapi generate ${PYGEOAPI_CONFIG} --output-file ${PYGEOAPI_OPENAPI} && \
    pygeoapi asyncapi generate ${PYGEOAPI_CONFIG} --output-file /pygeoapi/local.asyncapi.yml

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -sf http://localhost:80/conformance || exit 1
