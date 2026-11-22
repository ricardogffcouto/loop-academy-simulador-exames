FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data ./data
COPY static ./static
RUN useradd --create-home app
ENV SIM_DB=/data/simulados.db
EXPOSE 8080
# the Fly volume arrives owned by root: hand it to the app user, then drop root before starting
CMD ["sh", "-c", "mkdir -p /data && chown app:app /data && exec setpriv --reuid=app --regid=app --init-groups uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips '*'"]
