FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 sandbox
WORKDIR /runner
COPY run_tool.py /runner/run_tool.py
USER sandbox

ENTRYPOINT ["python", "/runner/run_tool.py"]
