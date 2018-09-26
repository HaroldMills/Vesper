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


import itertools
import re


_SEPARATOR = '.'
"""Annotation value component separator."""

_WILDCARD = '*'
"""Annotation value spec wildcard."""

_REGEXP_THAT_NEVER_MATCHES = 'a^'


# TODO: Move the contents of this module to the `Archive` class?


def create_string_annotation_values_regexp(annotation_value_specs):
    term_lists = [_create_regexp_terms(s) for s in annotation_value_specs]
    terms_list = list(itertools.chain.from_iterable(term_lists))
    if len(terms_list) == 0:
        return re.compile(_REGEXP_THAT_NEVER_MATCHES)
    else:
        return re.compile('|'.join(terms_list))


def _create_regexp_terms(annotation_value_spec):
    
    if annotation_value_spec == _WILDCARD:
        return [r'']
    
    elif annotation_value_spec.endswith(_SEPARATOR + _WILDCARD):
        prefix = _escape(annotation_value_spec[:-len(_WILDCARD)])
        return [r'^{}.+'.format(prefix)]
    
    elif annotation_value_spec.endswith(_WILDCARD):
        prefix = _escape(annotation_value_spec[:-len(_WILDCARD)])
        return [
            r'^{}$'.format(prefix),
            r'^{}.+'.format(prefix + _escape(_SEPARATOR))]

    else:
        return [_escape(annotation_value_spec)]


def _escape(s):
    return s.replace('.', r'\.')
