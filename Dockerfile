FROM python:3.11-slim


WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --upgrade pip

RUN pip install --default-timeout=100 --retries=10 --no-cache-dir --upgrade -r /code/requirements.txt -i https://pypi.org/simple
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
