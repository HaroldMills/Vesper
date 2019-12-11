# Tutorial

Welcome to the Vesper tutorial! In this tutorial, you will create a new Vesper archive (don't worry, we'll explain what that is in a moment), import an audio recording into it, and process the recording to find and classify some nocturnal flight calls (NFCs) that are in it. The tutorial will introduce several Vesper concepts (like what an archive is) as needed, with just enough explanation for the tutorial to make sense. For a more thorough explanation of Vesper concepts, see the [design](#design.md) section of the Vesper documentation.

## Contents

1. [Background](#background)
1. [Getting started](#getting-started)
1. [Importing data](#importing-data)
1. [Processing data](#processing-data)
1. [Exporting data](#exporting-data)

## Background

Before we begin the tutorial proper, this section will provide a little background about Vesper's design: how the application is structured, the kinds of data (audio and other) that Vesper processes, and the kinds of processing that Vesper can perform.

Vesper is a [web application](https://en.wikipedia.org/wiki/Web_application), and as such comprises two main components, the *server* and the *client*. The server provides access to a collection of data called a *Vesper archive* (or just *archive* for short) for one or more clients. The server typically runs on the same computer that holds the archive. The client runs in a web browser on either the same computer as the server or a different one. In this tutorial, we will run the server and the client on the same computer.

A Vesper archive is a collection of audio data, related metadata, and application configuration settings. Each archive has its own directory on disk, called the *archive directory*. The archive directory always contains certain essential parts of an archive, and in many cases the entirety of the archive.

Vesper supports four basic operations on archive data...

{% include figure.html url="images/vesper-data-operations.svg" caption="Figure 1: The four basic operations on Vesper data." %}

## Getting started

In this section of the tutorial, you will create a new Vesper archive, add a user to it, serve the archive with the Vesper server, and view the archive from a web browser.

### Create a new Vesper archive

The Vesper project provides a starter archive that you can copy...

### Add a user to the archive
### Start the Vesper server
### View the archive

## Importing data
    * Import archive data
    * Import a recording
## Processing data
    * Run automatic detectors
    * Run an automatic classifier
    * Classify clips manually
## Exporting data
    * Export clip audio files
