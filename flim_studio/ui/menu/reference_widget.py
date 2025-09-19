from typing import Dict, Optional
from dataclasses import dataclass

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
	QWidget,
	QVBoxLayout,
	QGroupBox,
	QFormLayout,
	QPushButton,
	QHBoxLayout,
	QLineEdit,
	QFileDialog,
	QLabel,
	QDoubleSpinBox,
	QStyle
)

from .auto_spin_box import AutoDoubleSpinBox
from .. import utils


class ReferenceWidget(QWidget):
	"""
	UI for loading a reference file for phasor calibration.
	"""
	def __init__(self, parent:Optional[QWidget]=None) -> None:
		super().__init__(parent)
		self._ref_path: str = ""

		self._build()

	## ------ Public API ------ ##
	def get_calibration(self):
		pass

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QVBoxLayout(self)

		box = QGroupBox("Reference (Calibration)")
		form = QFormLayout(box)

		# File selection button
		self.btn_browse_ref = QPushButton("Browse file...")
		self.btn_browse_ref.clicked.connect(self._on_browse_file)
		# File path display
		self.le_ref_path = QLineEdit()
		self.le_ref_path.setReadOnly(True)
		self.le_ref_path.setPlaceholderText("No file selected")
		# Parameter display
		self.laser_freq = AutoDoubleSpinBox()
		self.laser_freq.set_range(1.0, 1e3)
		self.laser_freq.set_suffix("MHz")
		self.laser_freq.set_value(80.0, as_default=True)

		self.ref_lifetime = AutoDoubleSpinBox()
		self.ref_lifetime.set_suffix("ns")
		self.ref_lifetime.set_value(4, as_default=True)
		# Make form
		form.addRow("Laser freq.", self.laser_freq)
		form.addRow("Ref. lifetime", self.ref_lifetime)

		layout.addWidget(self.btn_browse_ref)
		layout.addWidget(self.le_ref_path)
		layout.addWidget(box)


	## ------ Callbacks ------ ##
	def _on_browse_file(self) -> None:
		path, _ = QFileDialog.getOpenFileName(
			self,
			"Select reference file",
			self._ref_path or "",
			"FLIM files (*.tif *.tiff *.ptu);;All files (*)"
		)
		if not path:
			self.le_ref_path.setText("Invalid or unsupported file")
			self.le_ref_path.setStyleSheet(f"QLabel {{ background-color: {utils.COLOR_FAILURE}; }}");
			return

		self._ref_path = path
		self.le_ref_path.setText("Loading...")

		try:
			meta = load_reference(path)
		except ReferenceLoaderError as e:
			self.le_ref_path.setText(f"Error: {e}")
			return
		except Exception as e:
			self.le_ref_path.setText(f"Error: {type(e).__name__}")
			return

		self._apply_detected_meta(meta)
		self.le_ref_status.setText(path)
		self.le_ref_path.setStyleSheet(f"QLabel {{ background-color: {utils.COLOR_SUCCESS}; }}");
		#self.calibration_ready.emit(meta)  # bubble up for the app