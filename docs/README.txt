To build a local HTML version of the Vesper documentation:

    conda activate vesper-dev
    cd "/Users/harold/Documents/Code/Python/Vesper/docs"
    make html
    
View the local documentation at:

    file:///Users/harold/Documents/Code/Python/Vesper/docs/_build/html/index.html
    
To update the documentation at https://vesper.readthedocs.io, push to
the master branch of the Vesper GitHub repository. This will trigger
an automatic update on Read the Docs.
