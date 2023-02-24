# Dockerfile for development Vesper Docker image.
#
# This Dockerfile builds a development `vesper` Docker image that
# includes an editable `vesper` package in the `/Code` directory.
# When you run the image, you must mount the host file system
# directory containing the package's source code as the `/Code`
# directory in the container's file system.
#
# To build a production `vesper` Docker image, for example to upload
# to Docker Hub, it will make more sense to install an uneditable
# version of the `vesper` package in the Docker image, using
# `RUN pip install vesper` in place of the last several lines of
# this file, beginning with `WORKDIR /Code`.
#
# To build a `vesper` Docker image with this file, first create an
# up-to-date pip requirements.txt file as described below, and then
# issue the following command from the directory containing this file:
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
#        pip-freeze-creates-some-weird-path-instead-of-the-package-version)
#
#     4. Delete the `vesper` package line from the `requirements.txt` file
#        created in step 3.

# Pull base image.
FROM python:3.10.9-slim-bullseye

# Try the following instead of the above if your computer has a GPU.
#FROM tensorflow/tensorflow:2.11.0-gpu

# Set environment variables.
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory.
WORKDIR /Code

# Install Vesper dependencies.
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy Vesper project directory from host file system into image.
# The copy is used to install Vesper as an editable package in the
# next step. Note that when we run the image during development,
# we typically mount the project directory from the host file system
# as the `/Code` directory in the container file system, hiding the
# copy. Changes to the files of the mounted directory are thus
# visible from within the container.
COPY . .

# Install editable Vesper package.
RUN pip install -e .
