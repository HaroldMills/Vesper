Vesper
======

## Overview

Vesper is open source software for acoustic monitoring of nocturnal bird migration.

The goal of the Vesper project is to create software that will enable researchers and enthusiasts to collaboratively collect, view, and analyze nocturnal flight calls (NFCs) of migratory birds at spatial scales ranging from local to continental.

Vesper is a web application. As such, it comprises two parts, a *server* and a *client*. The server stores and processes audio data and metadata while the client runs in a web browser to provide the user interface. The server and client can run on the same computer for personal or small group use, or the server can run on a separate computer and serve multiple clients for larger deployments.

## Installation
Vesper is not ready for widespread use just yet, but for the intrepid there are preliminary [installation instructions](https://github.com/HaroldMills/Vesper/wiki/Installing-Vesper).

## Licensing and Acknowledgments

Vesper includes a copy of the [BirdVoxDetect](https://github.com/BirdVox/birdvoxdetect) nocturnal flight call detector, a product of the [BirdVox](https://wp.nyu.edu/birdvox/) project. BirdVoxDetect is covered by [this license](https://github.com/BirdVox/birdvoxdetect/blob/master/LICENSE). All other Vesper code is provided under [this license](https://github.com/HaroldMills/Vesper/blob/master/LICENSE).

BirdVoxDetect is described in:

    Robust Sound Event Detection in Bioacoustic Sensor Networks
    Vincent Lostanlen, Justin Salamon, Andrew Farnsworth, Steve Kelling, and Juan Pablo Bello
    Under review, 2019.

Many thanks to [MPG Ranch](http://mpgranch.com), Project Night Flight, [Old Bird](http://oldbird.org), and anonymous donors for financial support of the Vesper project.

![Image of Zenodo DOI badge](https://zenodo.org/badge/DOI/10.5281/zenodo.1020572.svg)
