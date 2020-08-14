***
FAQ
***

This section of the Vesper documentation answers frequently asked questions
(FAQs) regarding Vesper.

How can I modify the classification options displayed in Vesper?
================================================================

The Vesper user interface (UI) presents classification options in several
places, for example to let you specify which clips should be displayed in
a clip album or which clips you would like to export to audio files. The
options presented are determined by *annotation constraints* specified in
the archive database. When you create a new archive, you typically create
annotation constraints by importing a metadata YAML file using the
``Import metadata`` command, as in the `Vesper tutorial <tutorial.html>`_.

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

How can I modify the key bindings of a clip album?
==================================================

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
