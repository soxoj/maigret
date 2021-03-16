FROM python:3.7
LABEL maintainer="Soxoj <soxoj@protonmail.com>"

WORKDIR /app

ADD requirements.txt .

RUN pip install --upgrade pip

RUN apt update -y

RUN apt install -y\
      gcc \
      musl-dev \
      libxml2 \
      libxml2-dev \
      libxslt-dev \
&&  YARL_NO_EXTENSIONS=1 python3 -m pip install maigret \
&&  rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/*

ADD . .

ENTRYPOINT ["maigret"]
