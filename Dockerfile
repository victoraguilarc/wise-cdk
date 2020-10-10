FROM python:3.7-slim-buster as base

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y npm bash bash curl jq \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN npm install -g aws-cdk
RUN node -v

COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /requirements.txt

ENV CHAMBER_KMS_KEY_ALIAS=parameter_store_key

# env vars loader
RUN curl -sSL https://github.com/segmentio/chamber/releases/download/v2.8.2/chamber-v2.8.2-linux-amd64 > /chamber \
    && chmod +x chamber

WORKDIR /infra
