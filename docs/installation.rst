************
Installation
************

Installing Miniconda or Anaconda
================================

The Vesper installation instructions assume that you will use
Vesper in conjunction with either the
`Miniconda <http://conda.pydata.org/miniconda.html>`_ or the
`Anaconda <https://www.anaconda.com/distribution/>`_ Python
distribution. We recommend Miniconda and Anaconda due to their
excellent package and environment management functionality,
which makes it relatively easy to install and
maintain any number of Vesper versions and their dependencies.
You can read more about that functionality in the
`Conda environments`_ section below.

Miniconda and Anaconda are both free and open source, and are
offered by `Anaconda, Inc. <https://www.anaconda.com>`_, a
software company that specializes in scientific applications of
the Python programming language. Anaconda includes many packages,
some of which Vesper uses but most of which it doesn't. Miniconda
is much smaller than Anaconda, including only a minimal set of
packages. Either Miniconda or Anaconda is fine for use with
Vesper.

To install Miniconda, visit the `Miniconda home page
<http://conda.pydata.org/miniconda.html>`_ and follow
the instructions there for your platform. To install Anaconda,
visit the `Anaconda home page <https://www.anaconda.com/distribution/>`_
and follow the instructions there.

Installing Vesper
=================

.. Important::
   We strongly recommend installing each version of Vesper that you
   use into its own Conda environment (see the `Conda environments`_
   section below for an introduction to Conda environments). This has
   several advantages, including allowing you to easily revert to a
   previously installed Vesper version if you encounter problems with
   a new one.

To install the most recent version of Vesper in a new Conda environment:

1. If you don't have either the
   `Miniconda <http://conda.pydata.org/miniconda.html>`_ or the
   `Anaconda <https://www.anaconda.com/distribution/>`_ Python
   distribution already, download and install one of them.

2. Open a Windows Anaconda Prompt or Unix terminal.

3. Create a new Conda environment for Vesper and install a Python
   interpreter in it by issuing the command::

        conda create -n vesper-0.4.10 python=3.9

   Conda will display a list of packages that it proposes to install,
   including Python and some others. Press the ``Return`` key to accept.

4. Activate the environment you just created with::

        conda activate vesper-0.4.10

5. Install Vesper and various dependencies into the environment with::

       pip install vesper
       
   Here you must use pip rather than Conda since Vesper is distributed
   as a pip package. In addition to the Vesper package, pip will install
   several other packages on which Vesper depends, including, for example,
   ones for Django and SciPy.

Installing BirdVoxDetect (optional)
===================================

`BirdVoxDetect <https://github.com/BirdVox/birdvoxdetect>`_ is a
nocturnal flight call detector developed by the
`BirdVox <https://wp.nyu.edu/birdvox/>`_ project. While Vesper and
BirdVox are separate software development efforts, you can use
BirdVoxDetect from within Vesper just like any other supported
detector. For example, you can use Vesper to run BirdVoxDetect on
your recordings, view the resulting clips in clip albums, annotate
them with species classifications, etc.

If you would like to use BirdVoxDetect with Vesper, install
BirdVoxDetect separately in its own Conda environment. The
environment must have a name of the form:

        birdvoxdetect-<version number>

where ``<version number>`` is the number of the BirdVoxDetect version
installed in the environment, for example ``0.5.1``. The environment
must also include the ``vesper-birdvox`` package.

To create a Conda environment to use, say, BirdVoxDetect version 0.5.1
with Vesper:

1. Open a Windows Anaconda Prompt or Unix terminal.

2. Create a new Conda environment and install a Python interpreter in
   it by issuing the command::

        conda create -n birdvoxdetect-0.5.1 python=3.7

   Conda will display a list of packages that it proposes to install,
   including Python and some others. Press the ``Return`` key to accept.

4. Activate the environment you just created with::

        conda activate birdvoxdetect-0.5.1

5. Install the ``vesper-birdvox`` and ``birdvoxdetect`` packages and
   their dependencies into the environment with::

       pip install vesper-birdvox birdvoxdetect==0.5.1
       
To install a version of BirdVoxDetect other than 0.5.1, substitute
the appropriate version number for 0.5.1 in the instructions above,
and be sure to specify a Python version compatible with your
BirdVoxDetect version in step 2. See the installation instructions
for the specific BirdVoxDetect version you are installing for a list
of compatible Python versions.

Conda environments
==================

Miniconda and Anaconda both include a command line program called
`conda <https://conda.io/en/latest/index.html>`_. You can use conda
to manage multiple Python *environments* within your Miniconda or
Anaconda installation, where each environment contains a set of
software *packages*. For example, we strongly recommend installing
each version of Vesper that you use in its own conda environment.
Such an environment will include a Vesper package and several tens
of other packages on which Vesper depends, including, for example,
packages for Django, NumPy, and Python itself. Installing each
version of Vesper in its own environment keeps the packages for
those different versions from interfering with each other, and
with other packages that you might want to install in other,
non-Vesper environments.

Every Miniconda or Anaconda installation includes a default *base*
environment that is created automatically on installation. We do
*not* recommend installing Vesper in the base environment, but
rather in its own environment, as discussed above.

Conda environments are fully documented in the
`Managing environments <https://conda.io/projects/conda/user-guide/tasks/manage-environments.html>`_
section of the `conda documentation <https://conda.io/en/latest/index.html>`_.
We will describe only a few of the more common commands for managing
conda environments here.

Conda environments are managed mainly using the conda command line
program, which you can run from either the Windows Anaconda Prompt
or a Unix terminal. The Windows Anaconda Prompt program comes with
Miniconda and Anaconda, and is similar to the regular Command Prompt
program, except that it is customized for use with Miniconda and
Anaconda. The conda commands you type are the same on all platforms.
(If you are using Linux, however, note that some shell initialization
is required for the ``conda activate`` and ``conda deactivate`` commands
to work. Issue the ``conda init --help`` command for more about this.)

To create a new conda environment, issue the command::

    conda create -n <env> <package list>

where ``<env>`` is the name of the new environment (for example,
``vesper-1.0.0``) and ``<package list>`` is a list of packages that you
want to install. Conda will present you with a list of the Python
packages it proposes to install, including the ones you listed and
any other packages that they depend upon, and ask for confirmation
before proceeding.

To remove an environment named ``<env>``::

    conda remove -n <env> --all

To see a list of your environments::

    conda env list

To activate the environment named ``<env>`` in the current Windows
Anaconda Prompt or Unix terminal, issue the command::

    conda activate <env>

The name of the environment will subsequently appear at the
beginning of each command prompt in the window.

If an environment is active in the current Windows Anaconda Prompt
or Unix terminal, you can deactivate it with the command::

    conda deactivate
