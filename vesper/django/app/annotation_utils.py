"""
Constants and functions pertaining to annotations.

Several of the constants and functions below concern clip query
*annotation value specifications*. An annotation value specification,
or *annotation value spec* for short, is a string that describes a set
of clips in terms of their annotation status.

For a particular annotation, a clip can either be *unannotated*, meaning
that it has no value for that annotation, or it can be *annotated* with
some annotation value. An annotation value spec of "None" is used to
indicate the set of unannotated clips. In some cases, one can imagine
also wanting to use an actual annotation value of "None", but we
recommend against this to avoid confusion with the use of "None" to
indicate unannotated clips.

When an annotation value spec describes annotated clips, it specifies
the set of values with which they are annotated. The spec is said to
*match* an annotation value if the value is in the set. The simplest
sort of spec is just an annotation value, which matches itself. A spec
can also include a wildcard at its end to match muliple annotation
values. The wildcard can mean one of three things, depending on what
precedes it:

1. If the spec comprises just the wildcard (i.e. if nothing precedes
the wildcard), it matches any annotation value.

2. If the wildcard immediately follows the annotation value component
separator, it matches one or more annotation value components separated
by the separator. For example, values matched by the spec "Call.*"
include "Call.AMRE", "Call.BAWW", and "Call.One.Two".

3. If the wildcard immediately follows a character other than the
annotation value component separator, it matches either the empty
string or the separator followed by one or more annotation value
components separated by the separator. For example, values matched
by the spec "Call*" include "Call", "Call.AMRE", "Call.BAWW", and
"Call.One.Two".

In general, The pattern "<stuff>*" (as in the third case above) matches
the same annotation values as the pattern "<stuff>.*" (as in the second
case above), but also the value "<stuff>".

Finally, there is a special annotation spec "* | None" which, as you
might expect, indicates all clips, including both annotated and
unannotated ones.
"""


SEPARATOR = '.'
"""Annotation value component separator."""

WILDCARD = '*'
"""Annotation value spec wildcard."""

ANNOTATED_CLIPS = WILDCARD
"""
Annotation value spec for all annotated clips, regardless of annotation value.
"""

# TODO: Change this to 'None' when UI changes to handle more than just
# "Classification" annotation.
UNANNOTATED_CLIPS = 'Unclassified'
"""Annotation value spec for all unannotated clips."""

ALL_CLIPS = ANNOTATED_CLIPS + ' | ' + UNANNOTATED_CLIPS
"""Annotation value spec for all clips, whether annotated or not."""


def get_string_annotation_value_specs(annotation_values):
    
    """
    Gets a sorted list of annotation value specs derived from the
    specified annotation values.
    
    The list includes all of the specified values, as well as all
    ancestors of any multicomponent values that are present,
    """
    
    default_specs = [
        UNANNOTATED_CLIPS,
        ALL_CLIPS,
        ANNOTATED_CLIPS,
    ]
    
    specs = set()
    for value in annotation_values:
        specs.add(value)
        specs |= _get_string_annotation_value_specs(value)
        
    return default_specs + sorted(specs)
        
        
def _get_string_annotation_value_specs(annotation_value):
    components = annotation_value.split(SEPARATOR)
    specs = []
    for i in range(1, len(components)):
        spec = SEPARATOR.join(components[:i])
        specs.append(spec)
        specs.append(spec + WILDCARD)
        specs.append(spec + SEPARATOR + WILDCARD)
    return frozenset(specs)
