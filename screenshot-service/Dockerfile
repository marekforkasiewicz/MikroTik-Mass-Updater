FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir selenium

COPY *.py ./

CMD ["python", "screenshot.py"]
