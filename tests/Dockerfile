FROM python:3.10-alpine3.19

WORKDIR /tests

RUN apk add --no-cache python3 py-pip curl
RUN python3 -m venv /venv

RUN /venv/bin/python3 -m pip install --upgrade pip

ADD requirements.txt .
RUN /venv/bin/python3 -m pip install -r requirements.txt

CMD ["sh -c \"trap : TERM INT; sleep 604800 & wait\""]
