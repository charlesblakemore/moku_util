Basic Utilities for Acquiring and Analyzing Data from Moku:Go Devices
=====================================================================

This package mainly provides a class definition for handling Moku:Go
data, along with some basic utilities for plotting and data
manipulation. There are also some handler functions to initialize
and setup the Moku:Go devices for data acquisition, using the moku
Python API.

This code is intended for use by in the Stanford Physics Department,
for the course Physics 81L: Introduction to Experimental Practice.
Currently, the code only includes functionality for the 
spectroscopy lab.


Dependencies
------------

Required Python libraries are included in the requirements.txt file,
although with version unspecified. The Moku:Go devices force 
firmware updates, so it's presumed that all code will need to be 
updated at regular intervals to match the latest releases from
Liquid Instruments.

Aside from Python/Jupyter functionality, one also needs the 
MokuCLI tools (here: <https://apis.liquidinstruments.com/cli/>).
Ensure that the installed version matches that of the device 
firmware, otherwise you will not be able to connect.


Install
-------

From sources
````````````

Install in developer mode so any changes or updates to the code 
can be actively incorporated. Change the path if you're not in the
same directory::

   pip install -e ./moku_util

where pip is pip3 for Python3 (tested on Python 3.13.12).


Uninstall
---------

Uninstalling should be as easy as::

   pip uninstall moku_util


License
-------

The package is distributed under an open license (see LICENSE file for
information).


Authors
-------

Charles Blakemore (chas.blakemore@gmail.com)
