FROM geopython/pygeoapi:latest

# Copy configuration
COPY pygeoapi-config.yml /pygeoapi/local.config.yml
COPY data/ /data/
# Install custom HTML theme directly into the pygeoapi package templates directory.
# This is more reliable than the server.templates.path config option, which depends
# on the path being resolvable at runtime (not always the case on Railway/Fly).
COPY templates/base.html /tmp/gf-base.html
RUN python3 -c "import pygeoapi, os, shutil; d = os.path.join(os.path.dirname(pygeoapi.__file__), 'templates'); shutil.copy('/tmp/gf-base.html', os.path.join(d, 'base.html'))"

# FIX: Default env vars so the container starts correctly when no .env is present.
# PORT is overridden automatically by Railway. PYGEOAPI_SERVER_URL must be set
# manually to the public HTTPS URL after first deploy.
ENV PORT=80
ENV PYGEOAPI_SERVER_URL=http://localhost:5000

EXPOSE 80

# Create AsyncAPI document placeholder (required by pygeoapi startup check)
RUN echo "asyncapi: 2.6.0" > /pygeoapi/local.asyncapi.yml &&     echo "info:" >> /pygeoapi/local.asyncapi.yml &&     echo "  title: pygeoapi" >> /pygeoapi/local.asyncapi.yml &&     echo "  version: 1.0.0" >> /pygeoapi/local.asyncapi.yml &&     echo "channels: {}" >> /pygeoapi/local.asyncapi.yml
