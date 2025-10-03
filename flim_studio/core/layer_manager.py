from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
	import napari

class LayerManager:
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self, viewer:Optional["napari.Viewer"]):
		# HACK: A little hacky. We need to ensure that the first 
		# call to the constructor supplies the viewer.
		# Fortunately, it is clear the LayerManager will always be created in shell.
		# Since every module will be using it.
		if viewer:
			self.viewer = viewer
			# TODO: Wire events
		# Stores a nested dictionary containing the ndarray for layer
		# Keyed by:
		#	name: associated file name
		#	kind: the kind of layer this is
		self.layer_data = {}

	## ------ Public API ------ ##
	def add_image(self, name:str, image:np.ndarray, **kwarg) -> None:
		pass

	def get_layer_data(self, name:str, kind:str) -> np.ndarray:
		# Return the ndarray layer data stored at name:kind.
		# If none stored, return None.
		l1 = layer_data.get(name)
		return None if l1 is None else l1.get(kind)

	## ------ Internal ------ ##
	def _tag(self, name:str, kind:str) -> dict:
		return {
			"flimstudio": {
				"name": name,
				"kind": kind,
				"version": 1
			}
		}

	def _ensure_layer_exists(self, name:str, kind:str) -> None:
		layer = self._find_layer(name, kind)
		if layer is None:
			pass

	def _find_layer(self, name:str, kind:str) -> "napari.layers.Layer":
		"""
		Iterate through all layers and find first that has matching metadata.
		"""
		for lyr in self.viewer.layers:
			meta = getattr(lyr, "metadata", {})
			fs = meta.get("flimstudio")
			if fs and fs.get("name") == name and fs.get("kind") == kind:
				return lyr
		return None

	def _add_layer(self, name:str, kind:str) -> None:
		layer_data = self.get_layer_data(name, kind)

