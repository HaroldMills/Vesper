# To build a Docker image named "vesper", issue the following
# command from the directory containing this file:
#
#     docker build -t vesper .
#
# See the accompanying file `docker-compose.yaml` for how to use Docker
# Compose to serve a Vesper archive with the built image.
#
# Building a Docker image with this file requires an up-to-date pip
# requirements.txt file. Note that that file should be created using
# the command:
#
#     pip list --format=freeze > requirements.txt
#
# instead of the usual command:
#
#     pip freeze > requirements.txt
#
# in order to avoid a problem described at
# https://stackoverflow.com/questions/62885911/
# pip-freeze-creates-some-weird-path-instead-of-the-package-version

# Pull base image.
FROM python:3.10.4-slim-bullseye

# Try the following instead of the above if your computer has a GPU.
#FROM tensorflow/tensorflow:2.9.1-gpu

# Set environment variables.
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory.
WORKDIR /Code

# Install dependencies.
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy project.
COPY . .

# Install Vesper package.
RUN pip install -e .
