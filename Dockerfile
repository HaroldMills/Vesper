# To build a Docker image named "vesper", first create an up-to-date
# pip requirements.txt file (as described below), and then issue the
# following command from the directory containing this file:
#
#     docker build -t vesper .
#
# See the accompanying file `docker-compose.yaml` for how to use Docker
# Compose to serve a Vesper archive with the built image.
#
# Building a Docker image with this file requires an up-to-date pip
# `requirements.txt` file. To create that file:
#
#     1. Create an up-to-date `vesper-latest` environment as described
#        in `setup.py`.
#
#     2. Activate the `vesper-latest` environment.
#
#     3. From the directory containing this file, issue the command:
#
#            pip list --format=freeze > requirements.txt
#
#        Note that the recommended command differs from the usual one
#        (`pip freeze > requirements.txt`) for generating a
#        `requirements.txt` file in order to avoid a problem described
#        at https://stackoverflow.com/questions/62885911/
# pip-freeze-creates-some-weird-path-instead-of-the-package-version)
#
#     4. Delete the `vesper` package line from the `requirements.txt` file
#        created in step 3.

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
