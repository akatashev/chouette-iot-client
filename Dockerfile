FROM python:3.6-slim

WORKDIR /chouette-client
RUN pip3 install redis pytest pytest-cov

COPY . /chouette-client