FROM python:3.8-slim

WORKDIR /chouette-client
RUN pip3 install redis pytest pytest-cov

COPY . /chouette-client