FROM python:3.7-alpine
LABEL maintainer="Soxoj <soxoj@protonmail.com>"

WORKDIR /app

ADD requirements.txt .

RUN pip install --upgrade pip \
&& apk add --update --virtual .build-dependencies \
      build-base \
      gcc \
      musl-dev \
      libxml2 \
      libxml2-dev \
      libxslt-dev \
      jpeg-dev \
&&  YARL_NO_EXTENSIONS=1 python3 -m pip install maigret \
&&  apk del .build-dependencies \
&&  rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/*

ADD . .

ENTRYPOINT ["maigret"]
