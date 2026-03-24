FROM python:3.10-slim 

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN apt update && apt install -y procps

CMD ["uvicorn", "sys_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


