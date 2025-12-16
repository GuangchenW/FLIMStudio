from qtpy.QtCore import Signal
from qtpy.QtWidgets import QFrame

class Indicator(QFrame):
	"""
	An indicator widget with OFF and named ON states.

	- Pass 'states' as dict[str, str] mapping state name to hex color or CSS color.
	  If omitted, defaults to green, yellow, and red.
	- Call set_state("name") to turn ON with the corresponding color.
	- Call set_off() to turn OFF (gray).
	- Emits stateChanged(str) when state changes.
	"""
	stateChanged = Signal(str)

	def __init__(
		self,
		diameter: int = 12,
		*,
		states: dict[str, str] | None = None,
		off_color: str = "#bdc3c7",
		parent=None
	):
		super().__init__(parent)
		self._diameter = diameter
		self._off_color = off_color
		# TODO: Standarize these color schemes
		self._states = states or {
			"ok": "#2ecc71",
			"warn": "#f1c40f",
			"bad": "#e74c3c",
		}
		# current state name
		self._state_name: str = "off"

		self.setFixedSize(self._diameter, self._diameter)
		self.setStyleSheet("")
		self._apply()

	## ------ Public API ------ ##
	def set_off(self) -> None:
		self._set_state("off")

	def set_state(self, name:str) -> None:
		self._set_state(name)

	def state(self) -> str:
		return self._state_name

	## ------ Internal ------ ##
	def _set_state(self, name:str, silent:bool=False) -> None:
		if name != "off" and name not in self._states:
			raise KeyError(f"Unknown state name '{name}'. Allowed: {list(self._states)}")
		if name == self._state_name:
			return
		self._state_name = name
		self._apply()
		if not silent:
			self.stateChanged.emit(self._state_name)

	def _apply(self) -> None:
		color = self._off_color if self._state_name == "off" else self._states[self._state_name]
		r = self._diameter // 2
		self.setStyleSheet(f"QFrame{{background:{color}; border-radius:{r}px}}")