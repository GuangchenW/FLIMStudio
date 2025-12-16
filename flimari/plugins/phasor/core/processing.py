import numpy as np
from typing import List, Tuple
from scipy.ndimage import median_filter
from phasorpy.cursor import mask_from_circular_cursor

def labels_from_roi(
	real: np.ndarray,
	imag: np.ndarray,
	roi_list: List, # NOTE: I would do type hints here if not for the very annoying imports
) -> np.ndarray:
	"""
	Return a indexed label mask with the same dimension as the sample image,
	where the indices follow the order of the roi in roi_list.
	Note that the returned labels are 1-based, since 0 is reserved for background.
	"""
	l_center_real = [roi.real for roi in roi_list]
	l_center_imag = [roi.imag for roi in roi_list]
	l_radius = [roi.radius for roi in roi_list]
	# mask is a r x p 2d array where r is the number of rois and p is the length of real/imag.
	masks = mask_from_circular_cursor(real, imag, l_center_real, l_center_imag, radius=l_radius)
	# HACK: Given that the images are mostly likely equal width and height,
	# we just take the sqrt of the total length and reshape it based on that
	n, h, w = masks.shape

	# Build single integrated label mask
	labels = np.zeros((h,w), dtype=np.uint8) # Up to 255 rois
	for i in range(n):
		# Each m is a 2d binary array mask
		labels[masks[i]] = i+1

	return labels
