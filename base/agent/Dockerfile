FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 LP_BIND=0.0.0.0
WORKDIR /app
COPY pyproject.toml .
COPY lpagent ./lpagent
COPY fixtures ./fixtures
RUN pip install ".[pg]" && useradd --system --no-create-home agent
USER agent
EXPOSE 8090
CMD ["python", "-m", "lpagent.server"]
