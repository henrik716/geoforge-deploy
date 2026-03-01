FROM geopython/pygeoapi:latest

# Copy configuration
COPY pygeoapi-config.yml /pygeoapi/local.config.yml
COPY data/ /data/

# Tell Railway which port to route to
ENV PORT=80
EXPOSE 80

# Create AsyncAPI document placeholder (required by pygeoapi startup check)
RUN echo "asyncapi: 2.6.0" > /pygeoapi/local.asyncapi.yml &&     echo "info:" >> /pygeoapi/local.asyncapi.yml &&     echo "  title: pygeoapi" >> /pygeoapi/local.asyncapi.yml &&     echo "  version: 1.0.0" >> /pygeoapi/local.asyncapi.yml &&     echo "channels: {}" >> /pygeoapi/local.asyncapi.yml
