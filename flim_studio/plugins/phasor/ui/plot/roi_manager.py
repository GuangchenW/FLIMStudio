from __future__ import annotations
from typing import Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from matplotlib.patches import Circle
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QLineEdit,
	QLabel,
	QDoubleSpinBox,
	QPushButton,
	QListWidget,
	QListWidgetItem
)
from flim_studio.common.ui import ThemedButton, ColorButton

if TYPE_CHECKING:
	from matplotlib.axes import Axes

@dataclass
class Roi:
	name: str # ROI name
	real: float # center real
	imag: float # center imaginary
	radius: float # radius
	color: str # Hex color string

class RoiRowWidget(QWidget):
	"""
	ROI control row: name, radius spinbox, color button, remove button,
	and a Circle patch on a provided Matplotlib Axes.
	"""
	def __init__(
		self,
		name: str,
		ax: "Axes",
		viewer: "napari.Viewer",
		*,
		center: Tuple[float, float] = (0.5, 0.5),
		radius: float = 0.05,
		color: str = "#ff0000",
		parent: QWidget | None = None,
	) -> None:
		super().__init__(parent)
		self.name = name if name else "ROI"
		self.viewer = viewer
		self._ax = ax
		self._center = center
		self._color: str = color
		self._circle: Circle|None = None

		self._build_ui(radius, color)
		self._create_circle(center=center, radius=radius, color=color)

	## ------ UI ------ ##
	def _build_ui(self, init_radius:float, init_color:str) -> None:
		root = QHBoxLayout(self)

		self.btn_remove = ThemedButton(icon="delete", viewer=self.viewer)
		self.btn_remove.setToolTip("Delete ROI")
		self.btn_remove.clicked.connect(self._on_removal)
		root.addWidget(self.btn_remove)

		self.name_label = QLabel(self.name)
		self.name_label.setMaximumWidth(60)
		root.addWidget(self.name_label, stretch=1)

		self.radius = QDoubleSpinBox()
		self.radius.setRange(0.01, 99.0)
		self.radius.setSingleStep(0.01)
		self.radius.setValue(init_radius)
		self.radius.valueChanged.connect(self._on_radius_changed)
		root.addWidget(self.radius)

		self.btn_color = ColorButton(color=init_color)
		self.btn_color.colorChanged.connect(self._on_color_changed)
		root.addWidget(self.btn_color)

	## ------ Public API ------ ##
	def move_circle(self, real: float, imag: float) -> None:
		"""Move the circle to a new center."""
		if self._circle is None:
			self._create_circle(center=(real, imag), radius=self.radius.value(), color=self._color)
		else:
			self._circle.center = (real, imag)
		self._draw_idle()

	def remove_circle(self) -> None:
		"""Remove the circle patch from the axes."""
		if self._circle is not None:
			if self._circle.axes is not None:
				self._circle.remove()
			self._circle = None
			self._draw_idle()

	def to_data(self) -> Roi:
		"""
		Return roi as data struct.
		"""
		data = Roi(
			name = self.name,
			real = self._circle.center[0],
			imag = self._circle.center[1],
			radius = self._circle.radius,
			color = self.btn_color.get_color()
		)
		return data

	def bind(self, wlist:QListWidget, item:QListWidgetItem) -> None:
		self._list = wlist
		self._item = item

	## ------ Internal ------ ##
	def _create_circle(self, *, center:Tuple[float, float], radius:float, color:str) -> None:
		"""Create the circle with current settings and add to the axes."""
		# Clean up any existing patch first
		if self._circle is not None and self._circle.axes is not None:
			self._circle.remove()

		self._circle = Circle(
			center,
			radius=radius,
			fill=False,
			edgecolor=color,
			linewidth=1.5,
			zorder=10,
			picker=False,
		)
		self._ax.add_patch(self._circle)
		self._draw_idle()

	def _on_radius_changed(self, r: float) -> None:
		if self._circle is not None:
			self._circle.set_radius(r)
			self._draw_idle()

	def _on_color_changed(self, color:str) -> None:
		"""Update circle color from ColorButton (expects hex color string)."""
		self._color = color
		if self._circle is not None:
			self._circle.set_edgecolor(color)
			self._draw_idle()

	def _on_removal(self) -> None:
		if not (self._list and self._item):
			raise RuntimeError("Something is very wrong")
		r = self._list.row(self._item) # Get the row index
		self._list.takeItem(r) # Remove from list
		self.remove_circle() # Remove the cicular patch
		self.deleteLater() # Delete the widget; let gc handle the list item

	def _draw_idle(self) -> None:
		# We need this because there would be potentially many rois,
		# so we'd rather let them each row handle themselves.
		fig = self._ax.figure
		if fig and fig.canvas:
			fig.canvas.draw_idle()


class RoiManagerWidget(QWidget):
	def __init__(
		self,
		ax:Axes,
		viewer:"napari.Viewer",
		*,
		parent:QWidget|None=None
	):
		super().__init__(parent)

		self._ax = ax
		self._viewer = viewer 
		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		root = QVBoxLayout(self)

		self.le_roi_name = QLineEdit()
		self.le_roi_name.setPlaceholderText("Enter ROI name")
		self.btn_add_roi = QPushButton("Add ROI")
		self.btn_add_roi.clicked.connect(self._on_add_roi)
		layout = QHBoxLayout()
		layout.addWidget(self.le_roi_name)
		layout.addWidget(self.btn_add_roi)
		root.addLayout(layout)

		self.roi_list = QListWidget()
		root.addWidget(self.roi_list)

	## ------ Public API ------ ##
	def move_selected_roi(self, real:float, imag:float) -> None:
		"""
		Updated the position of selected ROI.
		"""
		item = self.roi_list.currentItem()
		if not item: return

		roi_row = self.roi_list.itemWidget(item)
		roi_row.move_circle(real, imag)

	def collect_roi(self) -> List[Roi]:
		"""
		Return a List of all existing ROI data in this manager.
		"""
		out = []
		for i in range(self.roi_list.count()):
			item = self.roi_list.item(i)
			widget = self.roi_list.itemWidget(item)
			if not widget: continue

			data = widget.to_data()
			out.append(data)
		return out

	## ------ Internal ------ ##
	def _on_add_roi(self) -> None:
		name = self.le_roi_name.text() # Get current name from lineedit
		roi_row = RoiRowWidget(name, self._ax, self._viewer)
		item = QListWidgetItem(self.roi_list)
		roi_row.bind(self.roi_list, item)
		item.setSizeHint(roi_row.sizeHint())
		self.roi_list.addItem(item)
		self.roi_list.setItemWidget(item, roi_row)
		# Select the newly created item immediately so user can move it right away
		self.roi_list.setCurrentItem(item)
		# Reset name lineedit
		self.le_roi_name.setText("")