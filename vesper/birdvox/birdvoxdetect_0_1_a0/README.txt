The vesper.birdvox.birdvoxdetect_0_1_a0.birdvoxdetect package is a slightly
modified copy of the 0.1.a0 release
(https://github.com/BirdVox/birdvoxdetect/releases/tag/0.1.a0) of the
BirdVoxDetect nocturnal flight call detector from the BirdVox project
(https://wp.nyu.edu/birdvox). See the LICENSE file accompanying this README
for a copy of the BirdVoxDetect license.

I modified the copy of BirdVoxDetect in Vesper in two simple ways:

1. I made the BirdVoxDetectError import in core.py relative instead of
   absolute so it will still work in its new package context in Vesper.

2. I commented out the logging code at the beginning of birdvoxdetect.__init__
   since it is redundant in the context of Vesper.

Of course, neither of these changes should affect the clips produced by the
detector.

I chose to include BirdVoxDetect in the Vesper package rather than having
Vesper users install it as a separate package mainly since it keeps Vesper
installation simple. Vesper and all of its dependencies are currently
installed with a single Conda command, and as far as I know there is not
yet a birdvoxdetect Conda package, only a pip package. There are other
advantages and disadvantages to including BirdVoxDetect in Vesper, so
that practice may change in the future.
