FROM python:3.8

COPY requirements.txt requirements.txt
COPY db.py db.py
COPY user.py user.py

RUN pip install -r requirements.txt

COPY . . 

CMD ["python", "./app.py"] 