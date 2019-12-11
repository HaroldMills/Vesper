# Tutorial

Welcome to the Vesper tutorial! In this tutorial, you will create a new Vesper archive, import an audio recording into it, and process the recording to find and classify some nocturnal flight calls (NFCs) that are in it. The tutorial will introduce several Vesper concepts (for example, what a Vesper archive is) as it goes along, with just enough explanation for the tutorial to make sense. For a more thorough explanation of Vesper concepts, see the [design](#design.md) section of the Vesper documentation.

## Contents

1. [Getting started](#getting-started)
2. [Importing data](#importing-data)
3. [Processing data](#processing-data)
4. [Exporting data](#exporting-data)

## Background

Before we embark on the tutorial proper, this section will provide a little background about Vesper's design: how the application is structured, the kinds of data (audio and other) that Vesper processes, and the kinds of processing that it can perform. In general, this tutorial will attempt to explain only what you need to understand about Vesper's design for the tutorial to make sense. The [design](#design.md) section of the Vesper documentation provides a more thorough explanation.

Vesper is a web application, and as such comprises two main components, the *server* and the *client*. The server provides access to a collection of data called a *Vesper archive* (or just *archive* for short) to one or more clients. The server typically runs on the same computer that holds the archive. The client runs in a web browser on either the same computer as the server or a different one. In this tutorial, we will run the server and the client on the same computer.

A Vesper archive is a collection of audio data, related metadata, and application configuration settings. Each archive has its own directory on disk, called the *archive directory*. While in some cases parts of an archive, such as its audio files, may be stored in one or more other directories or even on other disks, there is a single archive directory for each archive.

Vesper supports four basic operations on archives...

![Vesper Data Processing Figure](images/vesper-data-processing.svg)
Figure 1: The four basic Vesper data processing operations.

## Getting started

In this section of the tutorial, you will create a new Vesper archive, add a user to it, serve the archive with the Vesper server, and view the archive from a web browser.

But what is a Vesper archive?

A Vesper *archive* is a collection of audio data, related metadata, and application configuration settings.

* Create a new Vesper archive by creating a copy of the Vesper Starter Archive.
* Import an audio recording into the new archive.
* Process
### Create a new Vesper archive

The Vesper project provides a Vesper Starter Archive that you can copy 
### Add a superuser to the archive
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
