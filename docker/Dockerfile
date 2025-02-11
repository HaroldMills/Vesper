# Dockerfile for Vesper Docker images.
#
# You can build various Vesper Docker images using this file, depending
# on the command line arguments you provide. The `pypi`, `pypi-version`,
# `package`, and`source` target build stages of this file support builds
# from PyPI (latest or specific Vesper version), a local Python package
# file, and local source code, respectively. The `SIZE` and `VERSION`
# build arguments provide control of the Vesper package size (full or
# slim) and version (for builds from PyPI and local package files).
#
# Below are some example Docker build commands that use this file.
# All of the commands should be issued from the Vesper repository
# root directory, i.e. the parent directory of the directory containing
# this file.
#
#
# Latest full size Vesper from PyPI:
#
#     docker build -f docker/Dockerfile --target pypi -t vesper/vesper .
#
# Specific version of full size Vesper from PyPI:
#
#     docker build -f docker/Dockerfile --target pypi --build-arg VERSION=0.4.15 -t vesper/vesper .
#
# Full size Vesper from local package file:
#
#     docker build -f docker/Dockerfile --target package --build-arg VERSION=0.4.15 -t vesper/vesper .
#
# Full size Vesper from local source code:
#
#     docker build -f docker/Dockerfile --target source -t vesper/vesper .
#
# Slim Vesper from PyPI:
#
#     docker build -f docker/Dockerfile --target pypi --build-arg SIZE=_slim -t vesper/vesper-slim .
#
# Specific version of slim Vesper from PyPI:
#
#     docker build -f docker/Dockerfile --target pypi --build-arg SIZE=_slim --build-arg VERSION=0.4.15 -t vesper/vesper-slim .
#
# Slim Vesper from local package file:
#
#     docker build -f docker/Dockerfile --target package --build-arg SIZE=_slim --build-arg VERSION=0.4.15a0 -t vesper/vesper-slim .
#
# Slim Vesper from source code:
#
#     docker build -f docker/Dockerfile --target source --build-arg SIZE=_slim -t vesper/vesper-slim .
#
#
# Note that the `package` and `source` target build stages use `pip`
# requirements files, `requirements.txt` when building a full Vesper
# image and `requirements_slim.txt` when building a slim Vesper image.
# This use of the requirements files requires some extra setup, but it
# allows us to iterate more quickly during development. In particular,
# it allows us to separate Vesper dependency installation from Vesper
# package installation in the Vesper Dockerfile, so that Docker can
# cache the dependency installation step, so that it doesn't have to
# re-install the dependencies every time we change the Vesper source
# code.
#
# To create a `pip` requirements file for a Vesper package file
# <package file name> (e.g. `vesper-0.4.15.tar.gz`) located in Vesper's
# `dist` directory:
#
#     1. If there is a `vesper-reqs` Conda environment, delete it with:
#
#            conda remove -n vesper-reqs --all
#
#     2. `cd` to the directory containing this file.
#
#     3. Create a new `vesper-reqs` environment with:
#
#            conda create -n vesper-reqs python=3.11
#            conda activate vesper-reqs
#            pip install ../dist/<package file name>
#
#     4. Create a pip requirements file with:
#
#            pip list --format=freeze > <requirements file name>
#
#        Note that this command differs from the usual one
#        (`pip freeze > <requirements file name>`) for generating a
#        requirements file in order to avoid a problem described
#        at https://stackoverflow.com/questions/62885911/
#        pip-freeze-creates-some-weird-path-instead-of-the-package-version)
#
#     5. Delete the `vesper` package line from the requirements file
#        created in step 4.
#
#     6. Delete the `vesper-reqs` environment with:
#
#            conda deactivate
#            conda remove -n vesper-reqs --all



##### Base for other images #####

FROM python:3.11-slim-bookworm AS base

# You might try something like this instead of the above if your
# computer has a GPU.
#FROM tensorflow/tensorflow:2.12.0-gpu as base

# Vesper size, either "" (the default, for the full Vesper) or "_slim".
ARG SIZE=""

# Vesper version number, used only for installation from local package file.
ARG VERSION="0.4.15a0"

# Set environment variables.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run Daphne ASGI server for Vesper at port 8000.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "vesper.django.project.asgi:application"]



##### Latest version of Vesper installed from PyPI #####
FROM base AS pypi
RUN pip install --no-cache-dir vesper${SIZE} && pip cache purge



##### Specific version of Vesper installed from PyPI #####
FROM base AS pypi-version
RUN pip install --no-cache-dir vesper${SIZE}==${VERSION} && pip cache purge



##### Vesper installed from local package file #####

FROM base AS package

# Install full Vesper package dependencies. We separate this step from
# the Vesper package installation so we don't have to re-install all of
# the dependencies if only the Vesper package has changed.
COPY docker/requirements${SIZE}.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip cache purge

# Install full Vesper package.
COPY dist/vesper${SIZE}-${VERSION}.tar.gz ./vesper.tar.gz
RUN pip install --no-cache-dir vesper.tar.gz && rm vesper.tar.gz && pip cache purge



##### Vesper installed from source code in current directory #####

FROM base AS source

# Set working directory, creating it if needed.
WORKDIR /Code

# Install Vesper dependencies, using exactly the versions listed
# in `requirements.txt`.
COPY docker/requirements${SIZE}.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy Vesper project directory from host file system into image.
# The copy is used to install Vesper as an editable package in the
# next step. Note that when we run the image during development,
# we typically mount the project directory from the host file system
# as the `/Code` directory in the container file system, hiding the
# copy. Changes to the files of the mounted directory are thus
# visible from within the container.
COPY . .

# Install editable `vesper` Python package from `/Code` directory.
RUN pip install -e .
