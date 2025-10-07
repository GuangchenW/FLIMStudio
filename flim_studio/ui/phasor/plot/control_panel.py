from typing import List, Dict, Any, TYPE_CHECKING

from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QGroupBox,
	QGridLayout,
	QLabel,
	QSpinBox,
	QComboBox,
	QPushButton,
	QListWidget,
	QListWidgetItem
)

if TYPE_CHECKING:
	from .sample_manager_widget import Dataset

class PhasorControlPanel(QGroupBox):
	"""
	Control panel for phasor graph.
	Contains controls for adjusting plotting method and various filtering parameters.
	Also contains the ajustable list of datasets for this plotting instance.
	The user may select a non-empty subset from the list to work with.
	"""
	plotPhasor = Signal()
	mapRoi = Signal()

	def __init__(
		self,
		datasets: List["Dataset"],
		parent: QWidget|None = None
	) -> None:
		super().__init__("Control", parent)
		self._datasets = datasets

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		ctrl_grid = QGridLayout()
		ctrl_grid.setContentsMargins(5,15,5,5)
		self.setLayout(ctrl_grid)

		#  --- Left side: filter control
		# First row: intensity filter
		min_count_label = QLabel("Min photon count")
		max_count_label = QLabel("Max photon count")
		self.min_count = QSpinBox()
		self.min_count.setRange(0, int(1e9))
		self.max_count = QSpinBox()
		self.max_count.setRange(1, int(1e9))
		self.max_count.setValue(int(1e9))
		ctrl_grid.addWidget(min_count_label, 1, 1)
		ctrl_grid.addWidget(self.min_count, 1, 2)
		ctrl_grid.addWidget(max_count_label, 1, 3)
		ctrl_grid.addWidget(self.max_count, 1, 4)
		# Second row: median filter
		kernel_size_label = QLabel("Median filter size")
		repetition_label = QLabel("Median filter repetition")
		self.kernel_size = QSpinBox()
		self.kernel_size.setRange(1, 99)
		self.kernel_size.setValue(3)
		self.repetition = QSpinBox()
		self.repetition.setRange(0, 99)
		ctrl_grid.addWidget(kernel_size_label, 2, 1)
		ctrl_grid.addWidget(self.kernel_size, 2, 2)
		ctrl_grid.addWidget(repetition_label, 2, 3)
		ctrl_grid.addWidget(self.repetition, 2, 4)
		# Third row: plot mode and parameters
		mode_label = QLabel("Plot mode")
		self.mode_combo_box = QComboBox()
		self.mode_combo_box.addItem("contour")
		self.mode_combo_box.addItem("scatter")
		self.mode_combo_box.addItem("hist2d")
		ctrl_grid.addWidget(mode_label, 3, 1)
		ctrl_grid.addWidget(self.mode_combo_box, 3, 2)
		# Last row: Draw button
		self.btn_draw = QPushButton("Draw")
		self.btn_draw.clicked.connect(self._on_btn_draw_clicked)
		self.btn_map = QPushButton("Map ROI")
		self.btn_map.clicked.connect(self._on_btn_map_clicked)
		ctrl_grid.addWidget(self.btn_draw, 4, 1, 1, 2)
		ctrl_grid.addWidget(self.btn_map, 4, 3, 1, 2)

		# --- Right side: dataset management
		# A list widget where user can select dataset(s) to draw on the plot
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		for ds in self._datasets:
			list_item = QListWidgetItem(f"{ds.name} (channel {ds.channel})")
			self.dataset_list.addItem(list_item)
			# We want all datasets to be selected at the start
			# because we will immediately plot them
			list_item.setSelected(True)
		self.dataset_list.itemSelectionChanged.connect(self._on_selection_changed)
		self._on_selection_changed()
		ctrl_grid.addWidget(self.dataset_list, 1, 5, 4, 1)

	## ------ Public API ------ ##
	def get_selected_datasets(self) -> List["Dataset"]:
		return [
			self._datasets[self.dataset_list.row(item)]
			for item in self.dataset_list.selectedItems()
		]

	def get_params(self) -> Dict[str,Any]:
		"""
		Return a dictionary of control parameters. The keys match those in PhasorGraphWidget.draw_dataset.
		min_photon_count: minimum photon count
		max_photon_count: maximum photon count
		median_filter_size: median filter kernel size
		median_filter_repetition: median filter repetition
		mode: plotting mode
		"""
		params = {}
		params["min_photon_count"] = self.min_count.value()
		params["max_photon_count"] = self.max_count.value()
		params["median_filter_size"] = self.kernel_size.value()
		params["median_filter_repetition"] = self.repetition.value()
		params["mode"] = self.mode_combo_box.currentText()
		return params

	## ------ Internal ------ ##
	def _on_btn_draw_clicked(self) -> None:
		self.plotPhasor.emit()

	def _on_btn_map_clicked(self) -> None:
		self.mapRoi.emit()

	def _on_selection_changed(self) -> None:
		"""
		Disable the draw button if no dataset item is selected.
		"""
		has_selected = len(self.dataset_list.selectedItems())>0
		self.btn_draw.setEnabled(has_selected)
