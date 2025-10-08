from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from enum import Enum
import numpy as np

from napari.utils import DirectLabelColormap

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
	def add_layer(self, data:np.ndarray, *, name:str, kind:LayerType, overwrite:bool=False, **kwargs) -> None:
		"""
		Add a new napari layer or overwrite an existing one. 
		"""
		# If no data registered yet, register in dict.
		# Or, if data registered and overwrite, replace data.
		if self.get_layer_data(name, kind) is None or overwrite:
			self.layer_data.setdefault(name, {})[kind] = data
		# Check if layer already exists
		layer = self._find_layer(name, kind)
		if layer is None:
			# If no layer exists, add layer anyway
			self._add_layer(data, name, kind, **kwargs)
		elif overwrite:
			# if layer exists, update only if overwrite
			layer.data = self.get_layer_data(name, kind)
			# If it is label layer, we need to update colormap as well
			if kind == LayerType.LABEL:
				cmap = kwargs.pop("colormap", None)
				if cmap: layer.colormap = cmap

	def add_image(self, data:np.ndarray, *, name:str, overwrite:bool=False, **kwargs) -> None:
		self.add_layer(data, name=name, kind=LayerType.IMAGE, overwrite=overwrite, **kwargs)

	def add_label(self, data:np.ndarray, *, name:str, cdict:dict=None, overwrite:bool=False, **kwargs) -> None:
		cmap = DirectLabelColormap(color_dict=cdict) if cdict else None
		self.add_layer(data, name=name, kind=LayerType.LABEL, overwrite=overwrite, colormap=cmap, **kwargs)

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
		# This safely handles when user removed layer using built-in UI
		# and then uses the plugin buttons in data row.
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

	def _add_layer(self, data:np.ndarray, name:str, kind:LayerType, **kwargs) -> None:
		"""
		Helper function for add_layer. Performs the actual layer adding.
		"""
		# Make metadata
		tag = self._make_tag(name, kind)
		# Add layer
		match kind:
			case LayerType.IMAGE:
				self.viewer.add_image(data, name=name, metadata=tag, **kwargs)
			case LayerType.LABEL:
				self.viewer.add_labels(data, name=name, metadata=tag, **kwargs)
