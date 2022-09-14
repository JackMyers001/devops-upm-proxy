FROM python:3.10-alpine

WORKDIR /app

ADD requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Add code
ADD app.py .
ADD devops_scraping.py .
ADD enums.py .
ADD environmental_variables.py .
ADD mongo_functions.py .
ADD npm_classes.py .

CMD [ "python", "app.py" ]
