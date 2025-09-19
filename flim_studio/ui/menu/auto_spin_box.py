from typing import Optional

from qtpy.QtCore import Signal
from qtpy.QtGui import QPalette, QColor
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QDoubleSpinBox,
	QLineEdit,
	QPushButton,
	QStyle
)

import flim_studio.ui.utils as utils

class AutoDoubleSpinBox(QWidget):
	"""
	A labeled double spin box with:
		- a cached value that can be set
		- a Reset button that revertes the current value to the cached value
		- color hints for state:
			green  = cached value in use
			red    = no value cached
			blue   = value overridden by user
	"""
	valueChanged = Signal(float)       # re-emits spinbox valueChanged

	def __init__(self, parent:Optional[QWidget]=None) -> None:
		super().__init__(parent)

		# Cached detected value (if any)
		self.cached_value:float = 0.0
		self._overridden:bool = False
		self._has_cached:bool = True

		self._build()

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(6)

		self._spin = QDoubleSpinBox()
		self._spin.setRange(0.0, 1e9)
		self._spin.setSingleStep(0.01)
		self._spin.setValue(0.0)

		self._btn_reset = QPushButton()
		self._btn_reset.setToolTip("Reset to detected value")
		self._btn_reset.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
		self._btn_reset.setFixedWidth(28)
		self._btn_reset.setEnabled(False)

		layout.addWidget(self._spin, 1)
		layout.addWidget(self._btn_reset, 0)

		# Initial state = missing
		self._apply_bg(utils.COLOR_FAILURE)

		# Signals
		self._spin.valueChanged.connect(self._on_value_changed)
		self._btn_reset.clicked.connect(self.reset_to_cached)

	## ------ Public API ------ ##
	def set_range(self, minimum:float, maximum:float) -> None:
		self._spin.setRange(minimum, maximum)

	def set_decimals(self, decimals:int) -> None:
		self._spin.setDecimals(decimals)

	def set_step(self, step:float) -> None:
		self._spin.setSingleStep(step)

	def set_suffix(self, suffix: str) -> None:
		self._spin.setSuffix(suffix)

	def value(self) -> float:
		return float(self._spin.value())

	def set_value(self, value:float, as_default:bool=False) -> None:
		"""
		This always trigger value caching because there is no reason
		to set value if some program update did not occur.
		If as_default, current state will reset, treating value as the original.
		"""
		# This is a little hacky but ok
		self._spin.setValue(value)
		if as_default:
			self._overridden = False
			self._has_cached = False
			self.reset_button.setEnabled(False)
			self._apply_bg(utils.COLOR_FAILURE)
		else:
			self.cached_value = value
			self._overridden = False
			self._has_cached = True
			self.reset_button.setEnabled(True)
			self._apply_bg(utils.COLOR_SUCCESS)

	def reset_to_cached(self) -> None:
		"""Reset to the cached detected value (if present)."""
		if not self._has_cached: return
		self.set_value(self.cached_value)

	## ------ Accessors ------ ##
	@property
	def spinbox(self) -> QDoubleSpinBox:
		return self._spin

	@property
	def reset_button(self) -> QPushButton:
		return self._btn_reset

	## ------ Internals ------ ##
	def _on_value_changed(self, val:float) -> None:
		_overridden = True
		self._apply_bg(utils.COLOR_OVERRIDDEN)
		self.valueChanged.emit(val)

	def _apply_bg(self, color_hex: str) -> None:
		self._spin.setStyleSheet(f"QDoubleSpinBox {{ background: {color_hex}; }}")