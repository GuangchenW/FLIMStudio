import os
from pathlib import Path
from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
import xarray

import numpy as np
from phasorpy.phasor import phasor_from_signal
if TYPE_CHECKING:
	import napari

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

from flim_studio.core.calibration import Calibration
from flim_studio.core.io import load_signal
from .phasor_plot_widget import PhasorPlotWidget

@dataclass
class Dataset:
	path: str|Path
	name:str
	channel: int
	signal: xarray.DataArray # phasorpy signal
	mean: Optional[np.ndarray] = None # Average signal
	real: Optional[np.ndarray] = None # Real phasor coords
	imag: Optional[np.ndarray] = None # Imaginary phasor coords

class DatasetRow(QWidget):
	show_clicked = Signal()

	def __init__(
		self,
		name:str,
		dataset:Dataset,
		viewer:"napari.Viewer",
		parent:Optional[QWidget]=None
	):
		super().__init__(parent)
		self.name = name
		self.dataset = dataset
		self.viewer = viewer
		self._list: QListWidget|None = None
		self._item: QListWidgetItem|None = None
		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QHBoxLayout(self)
		self.label = QLabel(self.name)
		self.btn_delete = self._make_delete_button(self.viewer)
		self.btn_delete.clicked.connect(self._on_removal)
		self.btn_show = self._make_show_button(self.viewer)
		self.btn_show.clicked.connect(self._on_show)
		self.btn_show.setEnabled(False)
		# Since I am too lazy to implement a confirm delete dialog,
		# put label in the middle to prevent missclick of buttons
		layout.addWidget(self.btn_delete, 0)
		layout.addWidget(self.label, 1)
		layout.addWidget(self.btn_show, 0)

	def _make_delete_button(self, viewer) -> QPushButton:
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

	def _make_show_button(self, viewer) -> QPushButton:
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

	## ------ Public API ------ ##
	def bind(self, listw:QListWidget, item:QListWidgetItem) -> None:
		"""
		Bind the associated list widget item and parent list so removal is easier.
		"""
		self._list = listw
		self._item = item

	def compute_phasor(self, calibration:Optional[Calibration]=None) -> None:
		"""
		Compute the phasor coordinate of dataset.
		If calibration is provided, calibrate the phasor coordinated accordingly. 
		"""
		self.dataset.mean, self.dataset.real, self.dataset.imag = phasor_from_signal(self.dataset.signal, axis='H')
		if not calibration is None:
			self.dataset.real, self.dataset.imag = calibration.compute_calibrated_phasor(self.dataset.real, self.dataset.imag)
		self.btn_show.setEnabled(True)

	## ------ Internal ------ ##
	def _on_removal(self) -> None:
		if not (self._list and self._item):
			raise RuntimeError("Something is very wrong")
			return
		r = self._list.row(self._item) # Get the row index
		self._list.takeItem(r) # Remove from list
		self.deleteLater() # Delete the widget; let gc handle the list item
		# TODO: Remove the associated layers

	def _on_show(self) -> None:
		# TODO: Figure out what the show button should do now that 
		# we have a separate button for visualization.
		if self.btn_show.isChecked():
			# Show
			pass
		else:
			# Hide
			pass

class SampleManagerWidget(QWidget):
	def __init__(
		self,
		viewer: "napari.viewer.Viewer",
		calibration: Calibration,
		parent: Optional[QWidget]=None,
	):
		# NOTE: The theme is passed around because it is needed for determining 
		# the icon to use depending on lihgt and dark theme. Maybe it's better 
		# to pass the viewer around instead, but for now this will do.
		super().__init__(parent)
		self.viewer = viewer
		self.calibration = calibration
		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)

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

		# Control buttons
		self.btn_compute = QPushButton("Calculate selected")
		self.btn_compute.clicked.connect(self._on_compute_selected)
		self.btn_compute.setEnabled(False)
		self.btn_visualize = QPushButton("Visualize selected")
		self.btn_visualize.clicked.connect(self._on_visualize_selected)
		self.btn_visualize.setEnabled(False)
		button_row = QHBoxLayout()
		button_row.addWidget(self.btn_compute)
		button_row.addWidget(self.btn_visualize)

		# Dataset list
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		self.dataset_list.itemSelectionChanged.connect(self._on_selection_changed)

		root.addLayout(load_row)
		root.addLayout(button_row)
		root.addWidget(self.dataset_list)

	## ------ Public API ------ ##
	def get_selected_rows(self) -> List[DatasetRow]:
		"""
		Return the selected DatasetRow QWidget.
		"""
		selected = self.dataset_list.selectedItems()
		return [self.dataset_list.itemWidget(item) for item in selected]

	def get_selected_datasets(self) -> List[Dataset]:
		"""
		Return the list of selected Dataset dataclass instance.
		"""
		return [row.dataset for row in self.get_selected_rows()]

	## ------ Internal ------ ##
	def _on_browse_file(self) -> None:
		"""
		Prompt for file selection, then load file as phasorpy signal.
		Store the loaded signal as Dataset object along with metadata.
		Then create a DatasetRow and insert into the list widget. 
		"""
		paths, _ = QFileDialog.getOpenFileNames(
			self,
			"Select sample file(s)",
			"",
			"FLIM files (*.tif *.tiff *.ptu);;All files (*)"
		)
		selected_channel = self.channel_selector.value()
		for path in paths:
			name = os.path.basename(path)
			# TODO: Do we need to handle channel exception here? Or leave it to napari
			signal = load_signal(path, selected_channel) # Process selected channel into signal
			ds = Dataset(path=path, name=name, channel=selected_channel, signal=signal)

			item = QListWidgetItem(self.dataset_list)
			row = DatasetRow(f"{name} (channel {selected_channel})", ds, self.viewer)
			row.bind(self.dataset_list, item) 
			item.setSizeHint(row.sizeHint())
			self.dataset_list.addItem(item)
			self.dataset_list.setItemWidget(item, row)
	
	def _on_selection_changed(self) -> None:
		"""
		Only for determining the active state of compute and visualize buttons.
		Disable the buttons if no item is selected.
		"""
		has_selected = len(self.dataset_list.selectedItems())>0
		self.btn_compute.setEnabled(has_selected)
		self.btn_visualize.setEnabled(has_selected)

	def _on_compute_selected(self) -> None:
		"""
		Get the DatasetRow widget in the list items and make them compute phasor given the calibration.
		"""
		rows = self.get_selected_rows()
		for r in rows:
			r.compute_phasor(self.calibration)
	
	def _on_visualize_selected(self) -> None:
		"""
		Take all selected datasets, filter for those that have phasor computed,
		Instantiate a new PhasorPlorWidget instance and initialize with the datasets.
		If no selected datasets have phasor, simply return.
		"""
		datasets = self.get_selected_datasets()
		# Filter for datasets that has phasor computed
		datasets = [ds for ds in datasets if ds.mean is not None]
		if len(datasets) <= 0: return
		# Make plot widget
		phasor_plot_widget = PhasorPlotWidget(self.viewer, datasets, frequency=self.calibration.frequency)
		# NOTE: For some reason, area="right" leads to layout problems of the canvas. I'm unsure why.
		phasor_plot_dock = self.viewer.window.add_dock_widget(phasor_plot_widget, name="Phasor Plot", area="bottom")
		phasor_plot_dock.setFloating(True)
		phasor_plot_dock.setAllowedAreas(Qt.NoDockWidgetArea)