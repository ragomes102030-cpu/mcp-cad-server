# syntax=docker/dockerfile:1
# mcp-cad-cloud — cloud-ready MCP (ezdxf headless, sem AutoCAD)
# Render deploy (build with 'render services create')

FROM python:3.12-slim AS build

WORKDIR /app

# Install build deps
RUN pip install --no-cache-dir setuptools wheel

# Copy project
COPY cloud/ezdxf /app
COPY codigo /app/codigo

# Install the package
RUN pip install -e . --no-cache-dir

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime deps
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/mcp-cad-cloud /usr/local/bin/mcp-cad-cloud

EXPOSE 8000

ENV HOST=0.0.0.0     PORT=8000     CAD_BACKEND=ezdxf     CAD_TEMP=/tmp/mcp_cad

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["python", "-m", "mcp_cad_cloud.server"]
