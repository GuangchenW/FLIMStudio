import os
from pathlib import Path
from typing import Dict, Optional, List, TYPE_CHECKING

import numpy as np

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

from flim_studio.core.napari import LayerManager
from flim_studio.core.io import load_signal
from flim_studio.core.widgets import ThemedButton, Indicator
from .phasor_plot_widget import PhasorPlotWidget
from ..core import Dataset

if TYPE_CHECKING:
	import xarray
	import napari
	# HACK: still feels a bit hacky
	from .calibration_widget import CalibrationWidget
	from ..core import Calibration

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
		self._on_show()

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QHBoxLayout(self)
		self.label = QLabel(self.name)
		self.btn_delete = ThemedButton(icon="delete", viewer=self.viewer)
		self.btn_delete.setToolTip("Remove dataset")
		self.btn_delete.clicked.connect(self._on_removal)
		# TODO: Change behavior of eye button
		self.btn_show = ThemedButton(icon="visibility", viewer=self.viewer)
		self.btn_show.setToolTip("Focus in layer viewer")
		self.btn_show.clicked.connect(lambda : LayerManager().focus_on_layers(self.dataset.name))
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
		self.lifetime_combo_box.currentIndexChanged.connect(lambda i : self._on_show())
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

	def calibrate_phasor(self, calibration:"Calibration") -> None:
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
		if self.dataset is None:
			raise RuntimeError(f"Sample {name} does not have a dataset")
		# Show lifetime map
		match self.lifetime_combo_box.currentText():
			case "none":
				LayerManager().add_image(self.dataset.total, name=self.dataset.name, overwrite=True)
			case "phi":
				LayerManager().add_image(self.dataset.phase_lifetime, name=self.dataset.name, overwrite=True)
			case "M":
				LayerManager().add_image(self.dataset.modulation_lifetime, name=self.dataset.name, overwrite=True)
			case "proj":
				LayerManager().add_image(self.dataset.normal_lifetime, name=self.dataset.name, overwrite=True)

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
		# DANGER: manually changing phi_0 and m_0 does not trigger this
		for i in range(self.dataset_list.count()):
			item = self.dataset_list.item(i)
			row = self.dataset_list.itemWidget(item)
			row.mark_stale()
