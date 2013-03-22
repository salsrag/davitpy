# Waver module __init__.py
"""
*******************************
            WAVER
*******************************
This subpackage contains various utilities for WAVER,
the SuperDARN Wave Analysis Software Package.

DEV: functions/modules/classes with a * have not been developed yet

*******************************
"""
import sigio
from music import *
from signal import *
from sigproc import *
from compare import *
from xcor import *


# *************************************************************
# Define a few general-use constants

# Mean Earth radius [km]
Re = 6371.0
# Polar Earth radius [km]
RePol = 6378.1370
# Equatorial Earth radius [km]
ReEqu = 6,356.7523
