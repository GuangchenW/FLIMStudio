import os
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import xarray

import numpy as np
from napari.viewer import Viewer

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QGroupBox,
	QFormLayout,
	QPushButton,
	QLineEdit,
	QFileDialog,
	QLabel,
	QSpinBox,
	QListWidget,
	QListWidgetItem,
	QStyle
)

from flim_studio.core.io import load_signal

@dataclass
class Dataset:
	path: str|Path
	channel: int
	signal: xarray.DataArray # xarray
	real: Optional[np.ndarray] = None # Real phasor coords
	imag: Optional[np.ndarray] = None # Imaginary phasor coords

class _DatasetRow(QWidget):
	show_clicked = Signal()
	request_removal = Signal()

	def __init__(
		self,
		name:str,
		dataset:Dataset,
		theme:str,
		parent:Optional[QWidget]=None
	):
		super().__init__(parent)
		self.name = name
		self.dataset = dataset
		self.theme = theme
		self._list: QListWidget|None = None
		self._item: QListWidgetItem|None = None
		self._build()

	def _build(self) -> None:
		layout = QHBoxLayout(self)
		self.label = QLabel(self.name)
		self.btn_delete = QPushButton()
		self.btn_delete.setIcon(QIcon(f"theme_{self.theme}:/delete.svg"))
		self.btn_delete.setToolTip("Unload and remove dataset")
		self.btn_delete.clicked.connect(self._on_removal)
		self.btn_show = QPushButton()
		self.btn_show.setIcon(QIcon(f"theme_{self.theme}:/visibility_off.svg"))
		self.btn_show.setToolTip("Display image and phasor scatter")
		self.btn_show.clicked.connect(self.show_clicked.emit)
		layout.addWidget(self.label, 1)
		layout.addWidget(self.btn_delete, 0)
		layout.addWidget(self.btn_show, 0)

	def bind(self, listw:QListWidget, item:QListWidgetItem) -> None:
		self._list = listw
		self._item = item

	def _on_removal(self) -> None:
		if not (self._list and self._item):
			raise OSError("Something is very wrong")
			return
		r = self._list.row(self._item)
		self._list.takeItem(r)
		self.deleteLater()


class SampleManagerWidget(QWidget):
	def __init__(self, theme:str, parent:Optional[QWidget]=None):
		# NOTE: The theme is passed around because it is needed for determining 
		# the icon to use depending on lihgt and dark theme. Maybe it's better 
		# to pass the viewer around instead, but for now this will do.
		super().__init__(parent)
		self.theme = theme
		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QVBoxLayout(self)

		# File loading
		load_row = QHBoxLayout()
		self.le_channel = QLabel()
		self.le_channel.setText("Channel:")
		self.channel_selector = QSpinBox()
		self.channel_selector.setRange(0, 99)
		self.btn_browse_file = QPushButton("Browse file...")
		self.btn_browse_file.clicked.connect(self._on_browse_file)
		load_row.addWidget(self.le_channel)
		load_row.addWidget(self.channel_selector)
		load_row.addWidget(self.btn_browse_file)

		# Control
		self.btn_compute = QPushButton("Calculate phasor for selected")

		# Dataset list
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)

		layout.addLayout(load_row)
		layout.addWidget(self.btn_compute)
		layout.addWidget(self.dataset_list)

	## ------ Internal ------ ##
	def _on_browse_file(self) -> None:
		paths, _ = QFileDialog.getOpenFileNames(
			self,
			"Select sample file(s)",
			"",
			"FLIM files (*.tif *.tiff *.ptu);;All files (*)"
		)
		selected_channel = self.channel_selector.value()
		for path in paths:
			name = os.path.basename(path)
			signal = load_signal(path, selected_channel)
			ds = Dataset(path=path, channel=selected_channel, signal=signal)

			item = QListWidgetItem(self.dataset_list)
			row = _DatasetRow(f"{name} (channel {selected_channel})", ds, self.theme)
			row.bind(self.dataset_list, item)
			# TODO: row.show_clicked.connect()
			item.setSizeHint(row.sizeHint())
			self.dataset_list.addItem(item)
			self.dataset_list.setItemWidget(item, row)
	
	def _on_compute_selected(self) -> None:
		# TODO
		pass

	def selected_datasets(self) -> List[Dataset]:
		selected = self.dataset_list.selectedItems()
		return [item.dataset for item in selected]