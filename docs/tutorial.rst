********
Tutorial
********

Welcome to the Vesper tutorial! In this tutorial, you will create
a new Vesper archive (don’t worry if you don't know that that is:
we’ll explain in a moment), import an audio recording into it, and
process the recording to find and classify some bird calls that
are in it. The tutorial will introduce several Vesper concepts
(like what an archive is) as needed, with just enough explanation
for the tutorial to make sense. The concepts will be explained in
more detail in other parts of the documentation.

Background
==========

Before we begin the tutorial proper, this section will provide a
little background about Vesper: how the Vesper application is
structured, the kinds of data (audio and other) that it processes,
and the kinds of processing that it can perform.

Vesper is a
`web application <https://en.wikipedia.org/wiki/Web_application>`_,
and as such comprises two main components, a *server* and a
*client*. The server provides access to a collection of data called
a *Vesper archive* (or just *archive* for short) to one or more
clients, and performs operations on the data on behalf of the
clients. As a picture, this application architecture looks like
this:

.. figure:: _static/images/vesper-web-app.svg
   :alt: Vesper web application
   :align: center
   
   The architecture of the Vesper web application.
   
The server typically runs on the computer that holds the archive.
Each client runs in a web browser, either on the same computer as
the server or on a different one. In this tutorial, we will run
the server and a single client on the same computer.

A Vesper archive is a collection of audio data, related metadata,
and application configuration settings. Each archive has its own
directory on disk, called the *archive directory*. The archive
directory always contains certain essential parts of an archive,
and in many cases the entirety of the archive.

Vesper supports various operations on archive data. The
operations that you will perform in this tutorial fall into four
broad and common categories. These categories are illustrated in
the following figure:

.. figure:: _static/images/vesper-data-operations.svg
   :alt: Vesper data operations
   :align: center
   
   Four common types of operations on Vesper archive data.

An *import* operation imports audio data and/or related metadata
into an archive. For example, in this tutorial you’ll exercise two
different kinds of import operations, one for audio recordings and
another for metadata pertaining to them.

A *view* operation creates some sort of graphical representation of
data for you to view and in some cases interact with, for example
a spectrogram or a chart.

A *process* operation processes data, for example by running an
automatic detector or classifier, or by classifying a set of audio
clips according to a key that you type on your keyboard.

Finally, an *export* operation exports data from an archive for use
in other software. For example, in this tutorial you’ll export
detected bird calls from your archive as audio files.

Getting started
===============

Now that you're somewhat oriented to the Vesper web application
and Vesper archives, let's get started with the actual tutorial!
In this first part of the tutorial, you will create a new Vesper
archive, add a user to it, start a Vesper server to serve the
archive, and run the Vesper client in a web browser to view the
archive.

Download the Vesper archive template
------------------------------------

#. The Vesper project provides an archive template that you can copy
   to serve as a starting point for a new archive. Download the archive
   template to your computer by clicking `here
   <https://www.dropbox.com/s/4gdgqj10ksh5w3f/Vesper%20Archive%20Template.zip?dl=1>`_
   .

#. The template is packaged as a zip file: unzip it. This should yield a
   directory called ``Vesper Archive Template``.

Create a new Vesper archive
---------------------------

#. Copy the ``Vesper Archive Template`` directory to serve as your new
   archive directory. You can name the new archive directory whatever
   you want, for example ``Tutorial Archive``.
   
#. Open a Windows Anaconda Prompt or Unix terminal and activate your
   Vesper conda environment with a command like::

      conda activate vesper-x.y.z
      
   but with "vesper-x.y.z" replaced with the name of your Vesper
   environment. See the `Installation <installation.html>`_ section
   of this documentation for more about installation and conda
   environments.
      
#. In your Anaconda Prompt or terminal, cd to your new archive directory.
   For example, if you're on Windows and the archive
   directory path is ``C:\Users\Bailey\Desktop\Tutorial Archive``, the
   command is::
   
      cd "C:\Users\Bailey\Desktop\Tutorial Archive"
      
   An analogous command on macOS or Linux would look like::
   
      cd "/Users/Bailey/Desktop/Tutorial Archive"
   
#. Vesper stores the metadata of an archive in a relational database
   in the archive directory. The archive template doew not include
   such a database, however, so you have to create it. To create the
   database, issue the command::
   
      vesper_admin migrate
      
   This should create the SQLite database file
   ``Archive Database.sqlite`` in the archive directory.
      
#. Vesper keeps track of who makes what changes in an archive via the
   notion of a *user*. You can add any number of users to an archive,
   and you must log in as one of those users to be able to modify the
   archive. Every archive should have at least one *superuser*, a user
   with certain administrative privileges. Add a superuser to your
   archive database with the command::

      vesper_admin createsuperuser
      
   The command will prompt you for the superuser's name, email
   address, and password (twice). You can skip the email address if
   you wish. **Do not use a password that you really want to keep
   secret.** Communication between the Vesper client and server is
   currently unencrypted, so it is possible for someone eavesdropping
   on your client/server network traffic to see your password.

Start the Vesper server
-----------------------

In the Windows Anaconda prompt or Unix terminal of the last section,
issue the command::

   vesper_admin runserver
   
Some output from the server should appear in the terminal, indicating
that the server started.

View the archive
----------------

To run a Vesper client to view the archive:

#. Start a web browser. We recommend Chrome, since Vesper is tested and
   used most extensively with it.
   
#. Go to the URL:

      127.0.0.1:8000
      
   This should produce a page that looks something like this:
   
.. figure:: _static/images/empty-archive.png
   :alt: An empty Vesper archive.
   :align: center
   
   An empty Vesper archive.
   
Congratulations: you've created, served, and viewed your very own
Vesper archive! It doesn't contain any data yet, but you'll remedy
that in the next section.

Importing data
==============

Import metadata
---------------

Import a recording
------------------

Processing data
===============

Run automatic detectors
-----------------------

Run an automatic classifier
---------------------------

Classify clips manually
-----------------------

Exporting data
==============

Export clip audio files
-----------------------


