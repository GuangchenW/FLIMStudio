from typing import TYPE_CHECKING

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QGridLayout,
	QPushButton,
	QLineEdit,
	QComboBox,
	QLabel,
	QListWidget,
	QListWidgetItem,
)

from flim_studio.core.widgets import MPLGraph

if TYPE_CHECKING:
	from ..core import Dataset

class SummaryWidget(QWidget):
	def __init__(
		self,
		datasets:list["Dataset"],
		parent:QWidget|None = None
	):
		super().__init__(parent)
		self._datasets = datasets
		self._build()

	def _build(self) -> None:
		root = QVBoxLayout()
		self.setLayout(root)

		ctrl_grid = QGridLayout()
		ctrl_grid.setContentsMargins(5,15,5,5)
		root.addLayout(ctrl_grid)

		# Left: plot choices and button
		self.stats_combobox = QComboBox()
		# TODO: Add all stats options here
		self.stats_combobox.addItem("Placeholder")
		self.btn_plot = QPushButton("Plot selected")
		ctrl_grid.addWidget(self.stats_combobox, 1, 1)
		ctrl_grid.addWidget(self.btn_plot, 2, 1)

		# Middle: dataset list
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		for ds in self._datasets:
			list_item = QListWidgetItem(f"{ds.name} (channel {ds.channel})")
			self.dataset_list.addItem(list_item)
			list_item.setSelected(True)
		self.dataset_list.itemSelectionChanged.connect(self._on_selection_changed)
		ctrl_grid.addWidget(self.dataset_list, 1, 2, 2, 1)

		# Right: group assignment
		self.group_combobox = QComboBox()
		self.group_combobox.setEditable(True)
		self.group_combobox.setInsertPolicy(QComboBox.InsertAtTop)
		self.group_combobox.addItem("default")
		self.btn_assign_group = QPushButton("Group selected")
		self.btn_assign_group.setToolTip("Assign selected datasets to the group selected above")
		self.btn_assign_group.clicked.connect(self._on_btn_assign_group_clicked)
		# TODO: Connect signal
		ctrl_grid.addWidget(self.group_combobox, 1, 3)
		ctrl_grid.addWidget(self.btn_assign_group, 2, 3)
		# Init states of all buttons
		self._on_selection_changed()

		# Bottom: Graph
		self.graph = MPLGraph()
		root.addWidget(self.graph)

	## ------ Public API ------ ##
	def get_selected_datasets(self) -> list["Dataset"]:
		return [
			self._datasets[self.dataset_list.row(item)]
			for item in self.dataset_list.selectedItems()
		]

	## ------ Internal ------ ##
	def _on_btn_assign_group_clicked(self) -> None:
		datasets = self.get_selected_datasets()
		# TODO: Assign current selected group to the datasets

	def _on_selection_changed(self) -> None:
		"""
		Disable the plot and assign group button if no dataset item is selected.
		"""
		has_selected = len(self.dataset_list.selectedItems())>0
		self.btn_plot.setEnabled(has_selected)
		self.btn_assign_group.setEnabled(has_selected)