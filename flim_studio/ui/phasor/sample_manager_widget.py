import os
from pathlib import Path
from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field

import numpy as np
from phasorpy.phasor import phasor_from_signal
from phasorpy.lifetime import phasor_to_apparent_lifetime, phasor_to_normal_lifetime

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
	QComboBox,
	QFileDialog,
	QLabel,
	QSpinBox,
	QListWidget,
	QListWidgetItem,
	QStyle
)

from flim_studio.core import (
	load_signal,
	Calibration,
	LayerType,
	LayerManager,
)
from flim_studio.ui.custom import ThemedButton, Indicator
from .plot import PhasorPlotWidget

if TYPE_CHECKING:
	import xarray
	import napari
	from flim_studio.ui.phasor import CalibrationWidget

@dataclass
class Dataset:
	path: str|Path
	name: str
	channel: int
	signal: "xarray.DataArray"
	frequency: float = field(init=False) # Last used frequency
	mean: np.ndarray = field(init=False) # Mean signal
	real_raw: np.ndarray = field(init=False) # Raw real phasor
	imag_raw: np.ndarray = field(init=False) # Raw imaginary phasor
	real_calibrated: np.ndarray = field(init=False) # Calibrated real phasor
	imag_calibrated: np.ndarray = field(init=False) # Calibrated imaginary phasor
	g: np.ndarray = field(init=False) # Processed real coords, exactly as in graph
	s: np.ndarray = field(init=False) # Processed imaginary coords, exactly as in graph
	phase_lifetime: np.ndarray = field(init=False) # Apparent phase lifetime
	modulation_lifetime: np.ndarray = field(init=False) # Apparent modulation lifetime
	normal_lifetime: np.ndarray = field(init=False) # Projected lifetime

	def compute_phasor(self) -> None:
		"""
		Compute mean, real and imag, then sync all downstream properties.
		"""
		self.mean, self.real_raw, self.imag_raw = phasor_from_signal(self.signal, axis='H')
		self.frequency = self.signal.attrs.get("frequency", 0)
		# Calibrate without calibration to init other properties
		self.calibrate_phasor()

	def calibrate_phasor(self, calibration:Calibration=None) -> None:
		if calibration:
			self.real_calibrated, self.imag_calibrated = calibration.compute_calibrated_phasor(self.real_raw, self.imag_raw)
		else:
			self.real_calibrated = self.real_raw
			self.imag_calibrated = self.imag_raw
		self.g = self.real_calibrated
		self.s = self.imag_calibrated
		# Every time we re-calibrate, re-compute lifetime estimates
		if calibration and calibration.frequency > 0:
			self.frequency = calibration.frequency
		self.compute_lifetime_estimates()

	def compute_lifetime_estimates(self) -> None:
		"""
		Compute and cache apparent and projected lifetime.
		"""
		frequency = self.frequency if self.frequency > 0 else 80
		self._compute_apparent_lifetime(frequency)
		self._compute_normal_lifetime(frequency)

	def _compute_apparent_lifetime(self, frequency:float) -> None:
		self.phase_lifetime, self.modulation_lifetime = phasor_to_apparent_lifetime(self.g, self.s, frequency=frequency)

	def _compute_normal_lifetime(self, frequency:float) -> None:
		self.normal_lifetime = phasor_to_normal_lifetime(self.g, self.s, frequency=frequency)

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

		# Initialize phasor
		self.dataset.compute_phasor()
		self._build()
		self._add_image()

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QHBoxLayout(self)
		self.label = QLabel(self.name)
		self.btn_delete = ThemedButton(icon="delete", viewer=self.viewer)
		self.btn_delete.setToolTip("Remove dataset")
		self.btn_delete.clicked.connect(self._on_removal)
		self.btn_show = ThemedButton(icon="visibility", viewer=self.viewer)
		self.btn_show.setToolTip("Show estimated lifetime")
		self.btn_show.clicked.connect(self._on_show)
		# Dropbox for selecting the lifetime to visualize
		self.lifetime_combo_box = QComboBox()
		self.lifetime_combo_box.setToolTip((
			"Select lifetime estimations.\n'non': original signal\n'phi': apparent phase lifetime\n"
			"'M': apparent modulation lifetime\nproj: projected lifetime"
		))
		self.lifetime_combo_box.addItem("none")
		self.lifetime_combo_box.addItem("phi")
		self.lifetime_combo_box.addItem("M")
		self.lifetime_combo_box.addItem("proj")
		# Indicator for calibration status
		self.indicator = Indicator()
		self.indicator.set_state("bad")
		# Since I am too lazy to implement a confirm delete dialog,
		# put label in the middle to prevent missclick of buttons
		layout.addWidget(self.btn_delete, 0)
		layout.addWidget(self.label, 1)
		layout.addWidget(self.lifetime_combo_box, 0)
		layout.addWidget(self.btn_show, 0)
		layout.addWidget(self.indicator, 0)

	## ------ Public API ------ ##
	def bind(self, listw:QListWidget, item:QListWidgetItem) -> None:
		"""
		Bind the associated list widget item and parent list so removal is easier.
		"""
		self._list = listw
		self._item = item

	def calibrate_phasor(self, calibration:Calibration) -> None:
		"""
		Calibrate the phasor coordinate of dataset against the provided calibration.
		"""
		self.dataset.calibrate_phasor(calibration)
		self.indicator.set_state("ok")

	def mark_stale(self) -> None:
		"""
		Mark this dataset as stale (calibration has changed).
		"""
		if self.indicator.state() == "ok":
			self.indicator.set_state("warn")

	## ------ Internal ------ ##
	def _on_removal(self) -> None:
		if not (self._list and self._item):
			raise RuntimeError("Something is very wrong")
			return
		r = self._list.row(self._item) # Get the row index
		self._list.takeItem(r) # Remove from list
		self.deleteLater() # Delete the widget; let gc handle the list item
		# TODO: Remove the associated layers?

	def _on_show(self) -> None:
		# Show lifetime map
		match self.lifetime_combo_box.currentText():
			case "none":
				LayerManager().add_image(self.dataset.mean, name=self.dataset.name, overwrite=True)
			case "phi":
				LayerManager().add_image(self.dataset.phase_lifetime, name=self.dataset.name, overwrite=True)
			case "M":
				LayerManager().add_image(self.dataset.modulation_lifetime, name=self.dataset.name, overwrite=True)
			case "proj":
				LayerManager().add_image(self.dataset.normal_lifetime, name=self.dataset.name, overwrite=True)

	# Obsolete
	def _add_image(self) -> None:
		if self.dataset is None or self.dataset.mean is None:
			return
		# Add raw signal, i.e. HYX 3D signal
		# NOTE: axis_label is not shown in napari UI, it is internal only
		# WARNING: adding the 3D raw data causes axis order conflicts between data formats,
		# also the H dimension has weird behavior when there are multiple datsets with varying
		# H length. So it is best to just use averaged signal for now.
		LayerManager().add_image(self.dataset.mean, name=self.dataset.name)

class SampleManagerWidget(QWidget):
	def __init__(
		self,
		viewer: "napari.viewer.Viewer",
		cal_widget: "CalibrationWidget",
		parent: Optional[QWidget]=None,
	):
		# NOTE: The viewer is passed around because it is needed for determining 
		# the icon to use depending on lihgt and dark theme.
		super().__init__(parent)
		self.viewer = viewer
		# HACK: Still not a big fan of how this dependency is set up.
		# Ideally we don't need to inject this dependcy at all.
		self.calibration = cal_widget.calibration
		# Set up connect to update status od datasets
		cal_widget.calibrationChanged.connect(self._mark_all_stale)
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
		self.btn_calibrate = QPushButton("Calibrate selected")
		self.btn_calibrate.clicked.connect(self._on_calibrate_selected)
		self.btn_calibrate.setEnabled(False)
		self.btn_visualize = QPushButton("Visualize selected")
		self.btn_visualize.clicked.connect(self._on_visualize_selected)
		self.btn_visualize.setEnabled(False)
		button_row = QHBoxLayout()
		button_row.addWidget(self.btn_calibrate)
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
			row = DatasetRow(f"{name} (C{selected_channel})", ds, self.viewer)
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
		self.btn_calibrate.setEnabled(has_selected)
		self.btn_visualize.setEnabled(has_selected)

	def _on_calibrate_selected(self) -> None:
		"""
		Get the DatasetRow widget in the list items and make them compute phasor given the calibration.
		"""
		rows = self.get_selected_rows()
		for r in rows:
			r.calibrate_phasor(self.calibration)
	
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

	def _mark_all_stale(self) -> None:
		for i in range(self.dataset_list.count()):
			item = self.dataset_list.item(i)
			row = self.dataset_list.itemWidget(item)
			row.mark_stale()
