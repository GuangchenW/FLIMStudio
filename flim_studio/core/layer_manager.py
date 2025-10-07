from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from enum import Enum
import numpy as np

if TYPE_CHECKING:
	import napari

class LayerType(Enum):
	IMAGE = 1
	LABEL = 2

class LayerManager:
	_instance = None

	def __new__(cls, *arg, **kwarg):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self, viewer:Optional["napari.Viewer"]=None):
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
	def add_image(self, name:str, image:np.ndarray, overwrite:bool=False, **kwarg) -> None:
		self.layer_data.setdefault(name, {})[LayerType.IMAGE] = image
		self._update_layer(name, LayerType.IMAGE)

	def get_layer_data(self, name:str, kind:LayerType) -> np.ndarray:
		"""
		Return the ndarray layer data stored at <name,kind>.
		If none stored, return None.
		"""
		l1 = self.layer_data.get(name)
		return None if l1 is None else l1.get(kind)

	def remove_layer(self, name:str, kind:LayerType) -> None:
		"""
		Remove the first layer with the given metadata key.
		"""
		layer = self._find_layer(name, kind)
		print(layer)
		if layer is not None:
			self.viewer.layers.remove(layer)

	## ------ Internal ------ ##
	def _make_tag(self, name:str, kind:LayerType) -> dict:
		return {
			"flimstudio": {
				"name": name,
				"kind": kind,
				"version": 1
			}
		}

	def _update_layer(self, name:str, kind:LayerType, overwrite:bool=False) -> None:
		layer = self._find_layer(name, kind)
		if layer is None:
			self._add_layer(name, kind)
		elif overwrite:
			layer.data = self.get_layer_data(name, kind)

	def _find_layer(self, name:str, kind:LayerType) -> "napari.layers.Layer":
		"""
		Iterate through all layers and find first that has matching metadata.
		"""
		for lyr in self.viewer.layers:
			meta = getattr(lyr, "metadata", {})
			fs = meta.get("flimstudio")
			if fs and fs.get("name") == name and fs.get("kind") == kind:
				return lyr
		return None

	def _add_layer(self, name:str, kind:LayerType) -> None:
		"""
		Add a layer using the ndarray keyed by name and kind.
		Assumes the data has been registered in layer_data.
		"""
		layer_data = self.get_layer_data(name, kind)
		if layer_data is None: return
		# Make metadata
		tag = self._make_tag(name, kind)
		match kind:
			case LayerType.IMAGE:
				self.viewer.add_image(layer_data, name=name, metadata=tag)
			case LayerType.LABEL:
				pass
		print(type(self.viewer.layers))