from typing import TYPE_CHECKING
from napari.viewer import Viewer
from .app_shell import PhasorAnalysis

if TYPE_CHECKING: import napari

def open_phasor_analysis(viewer:Viewer) -> PhasorAnalysis:
	panel = PhasorAnalysis(viewer)
	viewer.window.add_dock_widget(panel, name="FLIM Studio", area="right")
	return panel