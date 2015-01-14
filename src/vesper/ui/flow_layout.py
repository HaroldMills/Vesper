"""Module containing `FlowLayout` class."""


'''
The following are notes made when developing the flow layout code.
The notes were originally part of a proof-of-concept script called
`LayoutTest` that has now been discarded. The notes may not reflect
exactly how the flow layout of this module works.

* User should specify height of clips panel in rows and width in seconds.

* Height in rows and width in seconds should not change across resizes.

* Separate layout completely from clip panel construction.

  Inputs:
    sequence of clip durations in seconds (perhaps a NumPy array?)
    minimum horizontal padding in seconds
    starting clip number
    number of rows to lay out (or `None` to lay out to end of clips)
    
  Outputs:
    sequence of starting clip indices for the laid out rows
    
  The layout algorithm does not concern itself with clip panel borders,
  only with the space (in seconds) allotted to displaying the clips
  themselves. When clip panels are subsequently constructed, they can be
  sized and positioned with the borders in mind. The assumption is that
  
* We may need layout to be very fast, since we would like to be able to
  deal with large numbers of clips. It would be great if we could lay out
  ten thousand clips in, say, a tenth of a second. If needed, we could
  construct an index into a list of clips that is a one-dimensional
  sequence whose ith entry gives us the index of the clip at cumulative
  time i * T, where T is something on the order of the average clip
  duration. This would make it unnecessary to consider the duration of
  every clip laid out during the layout itself, since much of the needed
  information would have been computed in advance.
'''


class FlowLayout(object):
    
    """
    Partitions a sequence of items with varying widths into rows with
    similar widths.
    """
    
    
    def __init__(self, max_row_size, spacing):
        self.max_row_size = max_row_size
        self.spacing = spacing
        
    
    def lay_out_items(self, item_sizes, start_item_num=0, max_num_rows=None):
        
        spacing = self.spacing
        
        # A row containing n items also contains n + 1 spaces, one
        # before each item and one at the end of the row. Here we
        # reduce the maximum row size by the spacing to account for
        # the spacing at the end of each row. Then in the rest of the
        # method we can conveniently assume that the number of items
        # and the number of spaces in a row are the same.
        max_row_size = self.max_row_size - spacing
        
        layout = []
        num_rows = 0
        row_start_item_num = start_item_num
        num_row_items = 0
        row_size = 0.
        num_items = len(item_sizes) - start_item_num
        item_num = start_item_num
        
        while num_rows != max_num_rows and item_num != num_items:
            
            size = spacing + item_sizes[item_num]
                
            if row_size + size <= max_row_size or num_row_items == 0:
                # item goes in this row
                
                num_row_items += 1
                row_size += size
                item_num += 1
                
            else:
                # item goes in next row
                
                layout.append(
                    (row_start_item_num, item_num - row_start_item_num))
                num_rows += 1
                row_start_item_num = item_num
                num_row_items = 0
                row_size = 0.
                
        if item_num != row_start_item_num:
            layout.append((row_start_item_num, item_num - row_start_item_num))
            
        return layout
