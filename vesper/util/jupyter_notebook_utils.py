"""Utility functions for use in Jupyter notebooks."""


import math

import matplotlib.pyplot as plt


def show_grams(grams, page_num, page_width=10, page_height=10):
    
    num_grams = len(grams)
    
    page_size = page_width * page_height
    num_pages = int(math.ceil(num_grams / float(page_size)))
    
    if page_num <= 0 or page_num > num_pages:
        
        print((
            'Invalid page number {}. Please specify a number in '
            '[{}, {}].').format(page_num, 1, num_pages))
        
    else:
        
        start_index = page_size * (page_num - 1)
        end_index = page_size * page_num
    
        print('Page {} of {}, grams {} to {} of {}'.format(
            page_num, num_pages, start_index + 1, end_index, num_grams))
        
        plt.figure(figsize=(12, page_height))

        for i, gram in enumerate(grams[start_index:end_index]):
            image = gram.transpose()
            plt.subplot(page_height, page_width, i + 1)
            plt.imshow(
                image, origin='lower', interpolation='none', cmap='gray_r')
            plt.axis('off')
