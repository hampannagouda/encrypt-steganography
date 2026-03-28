FROM python:3.10

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y g++
RUN g++ cpp/encrypt.cpp -o cpp/encrypt.exe -lcrypto

RUN pip install flask

CMD ["python", "app.py"]