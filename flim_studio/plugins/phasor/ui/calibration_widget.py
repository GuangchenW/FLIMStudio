from typing import Dict, Optional

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
	QWidget,
	QHBoxLayout,
	QVBoxLayout,
	QGroupBox,
	QFormLayout,
	QPushButton,
	QLineEdit,
	QFileDialog,
	QLabel,
	QSpinBox,
	QStyle
)

from flim_studio.core.widgets import AutoDoubleSpinBox
from ..core import Calibration


class CalibrationWidget(QWidget):
	"""
	UI for loading a reference file for phasor calibration.
	"""
	calibrationChanged = Signal()

	def __init__(self, parent:Optional[QWidget]=None) -> None:
		super().__init__(parent)
		self._ref_path: str = ""
		self.calibration = Calibration() # Calibration info container

		self._build()

	## ------ Public API ------ ##
	def get_calibration(self):
		"""
		Return the Calibration object
		"""
		return self.calibration

	## ------ UI ------ ##
	def _build(self) -> None:
		layout = QVBoxLayout(self)

		box = QGroupBox("Reference (Calibration)", self)
		form = QFormLayout()
		form.setContentsMargins(5,10,5,5)
		box.setLayout(form)

		# Channel selection
		# This must be determined by the user before loading the file
		self.le_channel = QLabel()
		self.le_channel.setText("Channel:")
		self.channel_selector = QSpinBox()
		self.channel_selector.setRange(-1, 99)
		# File selection button
		self.btn_browse_ref = QPushButton("Browse file...")
		self.btn_browse_ref.clicked.connect(self._on_browse_file)
		# File path display
		self.le_ref_status = QLineEdit()
		self.le_ref_status.setReadOnly(True)
		self.le_ref_status.setPlaceholderText("No file selected")
		# Acquisition parameters
		self.laser_freq = AutoDoubleSpinBox()
		self.laser_freq.set_range(1.0, 1e3)
		self.laser_freq.set_suffix("MHz")
		self.laser_freq.set_value(80.0, as_default=True)
		self.ref_lifetime = AutoDoubleSpinBox()
		self.ref_lifetime.set_suffix("ns")
		self.ref_lifetime.set_value(4, as_default=True)
		# Calibration button
		self.btn_compute = QPushButton("Compute calibration")
		self.btn_compute.clicked.connect(self._on_calibration_btn_pressed)
		self.btn_compute.setEnabled(False)
		# Calibration parameters
		self.phase_shift = AutoDoubleSpinBox()
		self.modulation_shift = AutoDoubleSpinBox()
		self.modulation_shift.set_value(1.0, as_default=True)
		# Make form
		row = QHBoxLayout()
		row.addWidget(self.le_channel)
		row.addWidget(self.channel_selector)
		row.addWidget(self.btn_browse_ref)
		form.addRow(row)
		form.addRow(self.le_ref_status)
		form.addRow("Laser freq.", self.laser_freq)
		form.addRow("Ref. lifetime", self.ref_lifetime)
		form.addRow(self.btn_compute)
		form.addRow("Phase", self.phase_shift)
		form.addRow("Modulation", self.modulation_shift)

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
			self.le_ref_status.setText("Invalid or unsupported file")
			return

		self._ref_path = path
		self.le_ref_status.setText("Loading...")

		# Load reference file and update status to file path
		try:
			channel = self.channel_selector.value()
			self.calibration.load(path, int(channel))
		except Exception as e:
			self.le_ref_status.setText(f"Error: {type(e).__name__}")
			return

		self.le_ref_status.setText(path)

		# Try to detect and set laser frequency
		freq = self.calibration.get_signal_attribute("frequency")
		if not freq is None:
			self.laser_freq.set_value(freq)

		# Finally, enable the calibration button
		self.btn_compute.setEnabled(True) 
		
	def _on_calibration_btn_pressed(self) -> None:
		frequency = self.laser_freq.value()
		lifetime = self.ref_lifetime.value()
		self.calibration.calibrate(frequency, lifetime)
		phi, m = self.calibration.get_calibration()
		self.phase_shift.set_value(phi)
		self.modulation_shift.set_value(m)
		self.calibrationChanged.emit()
