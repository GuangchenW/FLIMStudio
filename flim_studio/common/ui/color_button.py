from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
	QPushButton,
	QColorDialog,
)

class ColorButton(QPushButton):
	colorChanged = Signal(object)

	def __init__(self, *args, color:str="#ff0000", **kwargs):
		super().__init__(*args, **kwargs)

		self._color = None
		self._default = color
		self.set_color(self._default)
		self.pressed.connect(self._on_pick_color)

	## ------ Public API ------ ##
	def set_color(self, color):
		if color != self._color:
			self._color = color
			self.colorChanged.emit(color)

		if self._color:
			self.setStyleSheet(f"background-color: {self._color};")
		else:
			self.setStyleSheet("")

	def get_color(self):
		return self._color

	## ------ Internal ------ ##
	def _on_pick_color(self) -> None:
		dlg = QColorDialog(self.window())
		dlg.setStyleSheet("")
		if self._color:
			dlg.setCurrentColor(QColor(self._color))
		if dlg.exec_():
			self.set_color(dlg.currentColor().name())

	def mousePressEvent(self, e):
		if e.button() == Qt.RightButton:
			self.set_color(self._default)
		return super().mousePressEvent(e)