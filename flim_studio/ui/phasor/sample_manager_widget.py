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

	def __init__(
		self,
		name:str,
		dataset:Dataset,
		viewer:Viewer,
		parent:Optional[QWidget]=None
	):
		super().__init__(parent)
		self.name = name
		self.dataset = dataset
		self.viewer = viewer
		self._list: QListWidget|None = None
		self._item: QListWidgetItem|None = None
		self._build()

	def _build(self) -> None:
		layout = QHBoxLayout(self)
		self.label = QLabel(self.name)
		self.btn_delete = self.make_delete_button(self.viewer)
		self.btn_delete.clicked.connect(self._on_removal)
		self.btn_show = self.make_show_button(self.viewer)
		self.btn_show.clicked.connect(self._on_show)
		self.btn_show.setEnabled(False)
		# Since I am too lazy to implement a confirm delete dialog,
		# put label in the middle to prevent missclick of buttons
		layout.addWidget(self.btn_delete, 0)
		layout.addWidget(self.label, 1)
		layout.addWidget(self.btn_show, 0)

	def make_delete_button(self, viewer) -> QPushButton:
		btn = QPushButton()

		def apply_icons(*_):
			theme = getattr(viewer, "theme", "dark")
			icon = QIcon()
			icon.addFile(f"theme_{theme}:/delete.svg", mode=QIcon.Normal, state=QIcon.Off)
			btn.setIcon(icon)

		apply_icons() # Initialize the icons
		btn.setToolTip("Unload and remove dataset")
		# Keep in sync with theme
		viewer.events.theme.connect(apply_icons)
		return btn

	def make_show_button(self, viewer) -> QPushButton:
		btn = QPushButton()

		def apply_icons(*_):
			theme = getattr(viewer, "theme", "dark")
			icon = QIcon()
			# Enabled icon
			icon.addFile(f"theme_{theme}:/visibility.svg", mode=QIcon.Normal, state=QIcon.Off)
			icon.addFile(f"theme_{theme}:/visibility_off.svg", mode=QIcon.Disabled, state=QIcon.Off)
			btn.setIcon(icon)

		btn.setCheckable(True)
		apply_icons() # Initialize the icons
		# HACK: Showing tooltip covering both enabled and disabled state.
		# Better to make tooltips separate but I'm lazy.
		btn.setToolTip("""
			Show photon count average and phasor scatter.\n
			Disabled if the phasor has been calculated yet.
		""")
		btn.setAttribute(Qt.WA_AlwaysShowToolTips, True)
		# Keep in sync with theme
		viewer.events.theme.connect(apply_icons)
		return btn

	def bind(self, listw:QListWidget, item:QListWidgetItem) -> None:
		"""
		Bind the associated list widget item and parent list so removal is easier.
		"""
		self._list = listw
		self._item = item

	def _on_removal(self) -> None:
		if not (self._list and self._item):
			raise OSError("Something is very wrong")
			return
		r = self._list.row(self._item) # Get the row index
		self._list.takeItem(r) # Remove from list
		self.deleteLater() # Delete the widget; let gc handle the list item
		# TODO: Remove the associated layers

	def _on_show(self) -> None:
		if self.btn_show.isChecked():
			# Show image layers
			print("Checked")
		else:
			# Show image layers
			print("Unchecked")

class SampleManagerWidget(QWidget):
	def __init__(self, viewer:Viewer, parent:Optional[QWidget]=None):
		# NOTE: The theme is passed around because it is needed for determining 
		# the icon to use depending on lihgt and dark theme. Maybe it's better 
		# to pass the viewer around instead, but for now this will do.
		super().__init__(parent)
		self.viewer = viewer
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
		self.btn_compute.setEnabled(False)
		# TODO: set up connection 

		# Dataset list
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		self.dataset_list.model().rowsInserted.connect(self._on_list_item_added)
		self.dataset_list.model().rowsRemoved.connect(self._on_list_item_removed)

		layout.addLayout(load_row)
		layout.addWidget(self.btn_compute)
		layout.addWidget(self.dataset_list)

	## ------ Public API ------ ##
	def get_selected_datasets(self) -> List[Dataset]:
		selected = self.dataset_list.selectedItems()
		return [self.dataset_list.itemWidget(item).dataset for item in selected]

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
			row = _DatasetRow(f"{name} (channel {selected_channel})", ds, self.viewer)
			row.bind(self.dataset_list, item)
			# TODO: row.show_clicked.connect()
			item.setSizeHint(row.sizeHint())
			self.dataset_list.addItem(item)
			self.dataset_list.setItemWidget(item, row)
	
	def _on_list_item_added(self) -> None:
		# It's guaranteed that when this happens the list is non-empty
		self.btn_compute.setEnabled(True)

	def _on_list_item_removed(self) -> None:
		self.btn_compute.setEnabled(self.dataset_list.count()>0)

	def _on_compute_selected(self) -> None:
		# TODO
		pass