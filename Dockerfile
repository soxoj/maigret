FROM python:3.9-slim
LABEL maintainer="Soxoj <soxoj@protonmail.com>"
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
      gcc \
      musl-dev \
      libxml2 \
      libxml2-dev \
      libxslt-dev \
    && \
    rm -rf /var/lib/apt/lists/* /tmp/*
COPY . .
RUN YARL_NO_EXTENSIONS=1 python3 -m pip install --no-cache-dir .
ENTRYPOINT ["maigret"]
