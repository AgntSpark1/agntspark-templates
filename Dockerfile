# Builds one official template on top of the agent runtime image:
#
#   docker build --build-arg TEMPLATE=customer-support \
#     -t agntspark/template-customer-support:latest .
#
# The runtime (agntspark-core's `python -m agntspark_core serve`) loads
# /template/agent.yaml and its tool modules via AGNTSPARK_TEMPLATE_DIR and
# serves runtime contract v1 (GET /health, POST /invoke) on $PORT.

ARG RUNTIME_IMAGE=agntspark/agent-runtime:latest
FROM ${RUNTIME_IMAGE}

ARG TEMPLATE
LABEL org.opencontainers.image.title="AgntSpark template: ${TEMPLATE}"
LABEL org.opencontainers.image.source="https://github.com/AgntSpark1/agntspark-templates"
LABEL org.opencontainers.image.licenses="MIT"

USER root
COPY templates/${TEMPLATE}/ /template/
RUN test -f /template/agent.yaml || (echo "Unknown TEMPLATE '${TEMPLATE}'" >&2 && exit 1); \
    if grep -qv '^\s*\(#\|$\)' /template/requirements.txt 2>/dev/null; then \
        pip install -r /template/requirements.txt; \
    fi
USER agntspark

ENV AGNTSPARK_TEMPLATE_DIR=/template
