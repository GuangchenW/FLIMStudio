# Tutorials

Two example FLIM images, along with a reference image for phasor calibration, are provided alongside FLIMari. The two examples provided are IMSPECTOR TIFF and PicoQuant PTU, but the following tutorials are agnostic to user image formats.

## Import FLIM Data

FLIM files can be imported using the **Browse file...** button under the the *Dataset control* section in the FLIMari main panel.

![Dataset control](../img/dataset_control.png)
/// caption
Dataset control GUI
///

Files are selected through the native OS file manager dialog. Multiple files with different formats may be selected and imported at once. There is no upper limit to the number of files that can be imported at once, but loading many files may take a long time.

!!!note
    Only one channel is loaded at once for all selected files. If you want to analyze multiple channels in the same FLIM file, you can load the file multiple times, each time with a different channel specified.
    
    FLIMari channels are zero-based, meaning channel 0 is the first channel. 

## Manage FLIM Data

![Dataset list](../img/dataset_list.png)
/// caption
Dataset list GUI
///

Each item in the dataset list corresponds to an imported FLIM file. It is made of several interactable UI components:

* **Delete button**: Remove the dataset item and associated FLIM data.
* **Dataset name**: Formatted as `file_name(channel)[group_name]`.
* **Display mode**: How to display the FLIM data in the viewer. See (TODO) for more information.
* **Focus button**: Hide all other images in the viewer.
* **Status indicator**: Whether this dataset has been calibrated. 
    * Red = uncalibrated
    * Green = calibrated
    * Yellow = calibration has changed

Items in the list can be freely selected and deselected using `SHIFT+LEFT MOUSE CLICK` and `CTRL+LEFT MOUSE CLICK`. Most FLIMari operations on datasets only affect selected datasets in the list.

## Prepare Calibration

For accurate Phasor analysis of FLIM data, one must account for the effect of the [Instrument Response Function](https://www.tcspc.com/doku.php/howto:how_to_work_with_the_instrument_response_function_irf) (IRF).

FLIMari implements IRF correction using the **reference signal**. The reference signal is a FLIM file containing a sample with a known mono-exponential lifetime, acquired using the same microscope device and condition as the biological samples.

To calibrate FLIM data against a reference signal, first import the reference FLIM file in the calibration GUI.

![Calibration GUI](../img/calibration_gui.png)
/// caption
Calibration GUI
///

Calibration import accepts the same file formats as regular FLIM data. Likewise, it imports only the selected channel.

Once loaded, FLIMari will attempt to fetch the laser frequency from the file metadata. If successful, the `Laser freq.` input field will be set to the found value and turn green; otherwise, the value will need to be entered manually. `Ref. lifetime`, i.e. the fluorescence lifetime of the reference lifetime species, usually cannot be populated automatically and must be entered manually. 

After both `Laser freq.` and `Ref. lifetime` are set, press the **Compute calibration** button to calculate the calibration parameters `Phase` and `Modulation`. If successful, the input fields will be set to the calculated value and turn green. 

![Calibration Ready](../img/calibrated.png)
/// caption
Successfully computed calibration
///

!!!tip
    All automatically set values in the Calibration GUI can be manually overridden. Manually set fields will turn blue. Press the **Reset** button next to the input field to reset its value to the previously automatically set value.

## Calibrate Loaded Datasets

To calibrate datasets, simply select them in the [dataset list](tutorials.md#Manage FLIM data), then press the **Calibrate selected** button. The indicator lights will turn green once the calibration completes.

![Calibrate Phasor](../img/calibrate_phasor.png)
/// caption
Calibrate datasets
///

!!!tip
    Calibration parameters `Phase` and `Modulation` can be verified by importing the reference FLIM file as a regulat dataset, then calibrate it and confirm its phasor cloud centers on the universal semi-circle, at the correct lifetime position.