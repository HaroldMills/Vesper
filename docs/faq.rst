***
FAQ
***

This section of the Vesper documentation answers frequently asked questions
(FAQs) regarding Vesper.

When I start the Vesper server, it tells me I have "unapplied migrations". What does that mean, and what can I do about it?
===========================================================================================================================

It means that the relational database of your Vesper archive has an older
and different structure than that expected by your version of the Vesper
software. This kind of version mismatch can happen when you update Vesper
to a new version, or if somebody supplies you with an archive created with
an older version of Vesper than yours. The mismatch may (or may not,
depending on the particular differences) make it impossible for Vesper to
work properly with the database.

The process of updating the structure of your database is called
*migration*, and it is typically straightforward. To migrate your
database:

1. Make a backup copy of the ``Archive Database.sqlite`` database file
   that's in your archive directory.
   
.. WARNING::
   Always make a copy of your archive database before migrating it.
   Then if something goes wrong with the migration, you can always
   recover by restoring the original version of the database from
   your copy. If you don't make a copy of your database and the
   migration fails, you may lose some or all of your data!
   
2. Run the command:

        vesper_admin migrate
        
   in your archive directory from an Anaconda Prompt (on Windows) or
   terminal (on macOS or Linux). This should apply any needed migrations
   to your database to bring it up to date.
   
How do I use BirdVoxDetect with Vesper?
=======================================

`BirdVoxDetect <https://github.com/BirdVox/birdvoxdetect>`_ is a
nocturnal flight call detector developed by the
`BirdVox <https://wp.nyu.edu/birdvox/>`_ project. While Vesper and
BirdVox are separate software development efforts, you can use
BirdVoxDetect from within Vesper just like any other supported
detector. For example, you can use Vesper to run BirdVoxDetect on
your recordings, view the resulting clips in clip albums, annotate
them with species classifications, etc.

To use BirdVoxDetect with Vesper, first install it according to
Vesper's `BirdVoxDetect installation instructions
<https://vesper.readthedocs.io/en/latest/installation.html#installing-birdvoxdetect-optional>`_.
Then, add one or more BirdVoxDetect instances to your Vesper archive
as described in the answer to `this question
<faq.html#how-can-i-add-a-new-detector-to-a-vesper-archive>`_.
You can then run any of the BirdVoxDetect instances you added using
Vesper's ``Process->Detect`` command.

How do I add a new detector to a Vesper archive?
================================================

First, a note about terminology. Within Vesper, the term *detector*
is used in three different senses, and it is important to
understand how these senses differ to avoid confusion. The three
senses are termed *detector series*, *detector version*, and
*detector instance*, and they differ in their level of specificity.
A *detector series* is a sequence of *detector versions*, which
correspond to the usual notion of software versions. For example,
the ``BirdVoxDetect`` detector series has to date included several
versions, such as ``BirdVoxDetect 0.4.0``, ``BirdVoxDetect 0.4.1``,
and ``BirdVoxDetect 0.5.0``. Each detector version typically
has one or more *settings*, such as a detection threshold, whose
values must be specified before the detector can actually run. A
detector version plus a set of values for its settings is a
*detector instance*. Examples of ``BirdVoxDetect`` instances are
``BirdVoxDetect 0.5.0 FT 50``, which is version ``BirdVoxDetect 0.5.0``
with a fixed threshold of 50, and ``BirdVoxDetect 0.5.0 AT 40``,
which is the same version with an adaptive threshold of 40.

Currently, when you add a new detector to a Vesper archive, you
add a detector instance. There's no such thing (yet, at least)
as adding the detector series ``BirdVoxDetect`` to an archive, or
even the detector version ``BirdVoxDetect 0.5.0``. You always add
a detector instance, like ``BirdVoxDetect 0.5.0 FT 50``. With that
understood, in what follows we will use the term *detector* as a
shorthand for *detector instance*.

Vesper's ``Process->Detect`` command allows you to run one or more
detectors on a set of recordings. For a detector to appear in the
form for that command, it must first be added to the archive database.
You can do this with the ``File->Import metadata`` command.

It is common to import YAML metadata for one or more detectors when
you create an archive, as described in the `Importing data
<tutorial.html#importing-data>`_ section of the `Vesper tutorial`_.
See the example YAML metadata files of the tutorial, particularly the
``Processors`` sections of those files, for examples of detector
metadata.

It often happens, however, that after creating a Vesper archive and
using it for awhile, you decide that you would like to add a new
detector to the archive. This can happen for a variety of reasons.
A new detector version might appear in a detector series you've been
using, or you might want to try a new instance of a detector version
you've been using, say with a different detection threshold.

Suppose, for example, that you've been using the detector
``BirdVoxDetect 0.5.0 FT 50``, but would like to try
``BirdVoxDetect 0.5.0 FT 40``, i.e. the same detector version with
a lower threshold. To do that, you can create a YAML metadata file
for just the new detector and import it. Specifically, you can:

1. Create a text file (``BirdVoxDetect 0.5.0 FT 40.yaml``, say, but
   you can call it anything you'd like since Vesper doesn't care
   about the file name) with the following contents. Note that the
   first line should not have any leading space, and the other lines
   should be indented relative to the first exactly as shown:

   .. code-block:: yaml

      detectors:
          - name: BirdVoxDetect 0.5.0 FT 40
            description: BirdVoxDetect 0.5.0 NFC detector with a fixed threshold of 40.

2. Select ``File->Import metadata`` in Vesper to display the
   ``Import metadata`` form.

3. Drag your text file into the ``Metadata YAML`` text area of the form.
   The contents of the file should appear in the form.

4. Press the ``Import`` button to run the command.

5. After the command completes, restart the Vesper server for your
   archive to ensure that the server recognizes the new detector.

After these steps, the new detector should appear in all the appropriate
places in the Vesper user interface, for example in the ``Filter clips``
clip album modal and the ``Detect`` form.

Note that in the case of BirdVoxDetect, you must also make sure that
the appropriate version of BirdVoxDetect is installed on your system
in an appropriately-named Conda environment. See Vesper's `BirdVoxDetect
installation instructions
<https://vesper.readthedocs.io/en/latest/installation.html#installing-birdvoxdetect-optional>`_
for how to create such an environment.

How do I modify the classification options displayed in Vesper?
===============================================================

The Vesper user interface (UI) presents classification options in several
places, for example to let you specify which clips should be displayed in
a clip album or which clips you would like to export to audio files. The
options presented are determined by *annotation constraints* specified in
the archive database. When you create a new archive, you typically create
annotation constraints by importing a metadata YAML file using the
``File->Import metadata`` command, as in the `Vesper tutorial
<tutorial.html>`_.

If you later decide you would like to modify an annotation constraint,
for example to add or remove a species from it, you can do so using the
*Django admin interface*. Django is a third-party web framework used by
Vesper, and the admin interface is a set of web pages provided with
Django that allow you to edit your Vesper archive database. Eventually,
when the Vesper UI is more complete, it will never be necessary to use
the Django admin interface to edit Vesper archives, but as of this
writing it is still needed for some tasks.

.. WARNING::
   We strongly recommend that you make a copy of your archive database
   before you edit it with the Django admin interface. The archive
   database is contained in the file ``Archive Database.sqlite`` in your
   archive directory. If you make a copy of this file before editing it,
   then if you make a mistake in your editing, you can always recover
   from the mistake by restoring the original version of the database
   from your copy. If you don't make a copy of your database and
   accidentally mangle it with your edits, you may be very sorry!

To edit an annotation constraint with the Django admin interface, first
point your browser to the URL ``localhost:8000/admin``. Within that
interface, select ``Annotation constraints`` and then the name of the
constraint you want to edit, for example ``Classification``. This will
display a form that you can use to edit the selected constraint. The
constraint contains a YAML text field called ``Text``. The value of
that field is a YAML mapping that includes an item named ``values``
that you can edit to add or remove classification values.

Once you have edited an annotation constraint, you should restart your
Vesper server to be sure to pick up your changes.

How do I modify the key bindings of a clip album?
=================================================

Vesper clip albums allow you to type keys on your keyboard to invoke
a variety of *clip album commands*. For example, you might type ">"
to invoke a command to navigate to the next clip album page, "n" to
annotate the selected clip as a "Noise", or "/" to play the selected
clip. You can configure which keys (or key sequences) invoke which
commands using *clip album command presets*. Each of these presets is a
YAML file in the ``Presets/Clip Album Commands`` subdirectory of your
archive directory. To modify any of the presets, just use your favorite
text editor. After you edit a preset, you should restart your Vesper
server to be sure to pick up your changes.

Only one clip album command preset can be active at a time in a given
clip album. To choose the active preset for a clip album, select
``Choose presets...`` from the rightmost button to the right of the album's
title. To choose the default preset for your clip albums, edit the
``default_presets`` item in your archive preferences, stored in the file
``Preferences.yaml`` in your archive directory. After you edit this file,
you should restart your Vesper server to be sure to pick up your changes.
