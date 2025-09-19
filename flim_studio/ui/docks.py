from typing import TYPE_CHECKING
from napari.viewer import Viewer
from .app_shell import MainPanel

if TYPE_CHECKING: import napari

def open_main_panel(viewer:Viewer) -> MainPanel:
	panel = MainPanel(viewer)
	viewer.window.add_dock_widget(panel, name="FLIM Studio", area="right")
	return panel