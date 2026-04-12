FROM python:3.12-slim

WORKDIR /app

COPY site/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY site /app

EXPOSE 80

CMD ["gunicorn", "-b", "0.0.0.0:80", "app:app"]
