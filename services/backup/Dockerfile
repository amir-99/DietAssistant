FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends bash && rm -rf /var/lib/apt/lists/*

COPY scripts/backup.sh /usr/local/bin/backup.sh
COPY scripts/run_backup.py /usr/local/bin/run_backup.py
RUN chmod +x /usr/local/bin/backup.sh

CMD ["python", "/usr/local/bin/run_backup.py"]
