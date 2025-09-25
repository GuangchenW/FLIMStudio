from typing import TYPE_CHECKING

from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
	QWidget,
	QPushButton,
)

if TYPE_CHECKING:
	import napari

class RemoveButton(QPushButton):
	def __init__(self, *args, viewer:"napari.Viewer", **kwargs):
		super().__init__(*args, **kwargs)
		self.viewer = viewer
		self._apply_icons()
		viewer.events.theme.connect(self._apply_icons)

	def _apply_icons(self):
		theme = getattr(self.viewer, "theme", "dark")
		icon = QIcon()
		icon.addFile(f"theme_{theme}:/delete.svg", mode=QIcon.Normal, state=QIcon.Off)
		self.setIcon(icon)