# To build a Docker image named "vesper", issue the following
# command from the directory containing this file:
#
#     docker build -t vesper .
#
# See the accompanying file `compose.yaml` for how to use Docker Compose
# to serve a Vesper archive with the built image.

# Pull base image.
FROM python:3.10.4-slim-bullseye

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
