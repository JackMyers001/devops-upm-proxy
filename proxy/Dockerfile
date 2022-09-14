FROM python:3.10-alpine

WORKDIR /app

ADD requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Add code
ADD server.py .
ADD npm_classes.py .
ADD wsgi.py .

CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:8080", "wsgi"]
