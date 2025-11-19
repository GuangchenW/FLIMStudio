from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
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
		self.stats_items = [
			"photon_count",
			"phi_lifetime",
			"m_lifetime",
			"proj_lifetime",
		]
		self._build()

	def _build(self) -> None:
		root = QVBoxLayout()
		self.setLayout(root)

		ctrl_grid = QGridLayout()
		ctrl_grid.setContentsMargins(5,15,5,5)
		root.addLayout(ctrl_grid)

		# Left: plot controls
		self.stats_combobox = QComboBox()
		for item in self.stats_items:
			self.stats_combobox.addItem(item)
		self.btn_plot = QPushButton("Plot selected")
		self.btn_plot.clicked.connect(self._on_btn_plot_clicked)
		self.btn_clear = QPushButton("Clear plot")
		self.btn_clear.clicked.connect(self._on_btn_clear_clicked)
		ctrl_grid.addWidget(self.stats_combobox, 0, 0)
		ctrl_grid.addWidget(self.btn_plot, 1, 0)
		ctrl_grid.addWidget(self.btn_clear, 2, 0)

		# Middle: dataset list
		self.dataset_list = QListWidget()
		self.dataset_list.setSelectionMode(self.dataset_list.ExtendedSelection)
		self.dataset_list.setSpacing(0)
		for ds in self._datasets:
			list_item = QListWidgetItem(self._make_item_name(ds))
			self.dataset_list.addItem(list_item)
			list_item.setSelected(True)
		self.dataset_list.itemSelectionChanged.connect(self._on_selection_changed)
		ctrl_grid.addWidget(self.dataset_list, 0, 1, 3, 1)

		# Right: data control
		self.btn_export = QPushButton("Export selected")
		self.btn_export.setToolTip("Export selected datasets. Select all datasets to export all.")
		self.btn_export.clicked.connect(self._on_btn_export_clicked)
		ctrl_grid.addWidget(self.btn_export, 0, 2)
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
	def _on_btn_plot_clicked(self) -> None:
		datasets = self.get_selected_datasets()
		if len(datasets) == 0: return
		data = self._make_data_for_plot(datasets)
		ax = self.graph.get_ax()
		ax.violinplot(data.values())
		labels = data.keys()
		ax.set_xticks(np.arange(1, len(labels)+1), labels=labels)
		self.graph.draw_idle()

	def _make_data_for_plot(self, datasets:list["Dataset"]) -> None:
		data = {}
		for ds in datasets:
			summary = ds.summarize()
			values = summary[self.stats_combobox.currentText()]
			# Filter out nan
			values = values[~np.isnan(values)]
			group = summary["group"]
			data[group] = np.append(data.get(group, np.array([])), values)
		return data

	def _on_btn_clear_clicked(self) -> None:
		self.graph.clear()

	def _make_item_name(self, dataset:"Dataset") -> str:
		return f"{dataset.name} (channel {dataset.channel}) [{dataset.group}]"

	def _on_btn_export_clicked(self) -> None:
		pass
		# TODO: Implement data export

	def _on_selection_changed(self) -> None:
		"""
		Disable the plot and assign group button if no dataset item is selected.
		"""
		has_selected = len(self.dataset_list.selectedItems())>0
		self.btn_plot.setEnabled(has_selected)
