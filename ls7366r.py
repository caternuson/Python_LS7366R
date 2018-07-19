# The MIT License (MIT)
#
# Copyright (c) 2018 Carter Nelson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# MDR0 configuration data - the configuration byte is formed with
# single segments taken from each group and ORing all together.

COUNTER_BITS = (32, 24, 16, 8)
QUADRATURE_MODES = (0, 1, 2, 4)

# Count modes
NQUAD = 0x00          # non-quadrature mode
QUADRX1 = 0x01        # X1 quadrature mode
QUADRX2 = 0x02        # X2 quadrature mode
QUADRX4 = 0x03        # X4 quadrature mode

# Running modes
FREE_RUN = 0x00
SINGE_CYCLE = 0x04
RANGE_LIMIT = 0x08
MODULO_N = 0x0C

# Index modes
DISABLE_INDX = 0x00   # index_disabled
INDX_LOADC = 0x10     # index_load_CNTR
INDX_RESETC = 0x20    # index_rest_CNTR
INDX_LOADO = 0x30     # index_load_OL
ASYNCH_INDX = 0x00    # asynchronous index
SYNCH_INDX = 0x80     # synchronous index

# Clock filter modes
FILTER_1 = 0x00       # filter clock frequncy division factor 1
FILTER_2 = 0x80       # filter clock frequncy division factor 2

# MDR1 configuration data; any of these
# data segments can be ORed together

# Flag modes
NO_FLAGS = 0x00       # all flags disabled
IDX_FLAG = 0x10       # IDX flag
CMP_FLAG = 0x20       # CMP flag
BW_FLAG = 0x40        # BW flag
CY_FLAG = 0x80        # CY flag

# 1 to 4 bytes data-width
BYTE_4 = 0x00         # four byte mode
BYTE_3 = 0x01         # three byte mode
BYTE_2 = 0x02         # two byte mode
BYTE_1 = 0x03         # one byte mode

# Enable/disable counter
EN_CNTR = 0x00        # counting enabled
DIS_CNTR = 0x04       # counting disabled

# LS7366R op-code list
CLR_MDR0 = 0x08
CLR_MDR1 = 0x10
CLR_CNTR = 0x20
CLR_STR = 0x30
READ_MDR0 = 0x48
READ_MDR1 = 0x50
READ_CNTR = 0x60
READ_OTR = 0x68
READ_STR = 0x70
WRITE_MDR1 = 0x90
WRITE_MDR0 = 0x88
WRITE_DTR = 0x98
LOAD_CNTR = 0xE0
LOAD_OTR = 0xE4

class LS7366R():
    """LSI/CSI LS7366R quadrature counter."""

    def __init__(self, spi):
        # This should be a SpiDev or compatible object.
        self._spi = spi

        # Default config
        self._write_mdr0(QUADRX4 | FREE_RUN | DISABLE_INDX | FILTER_1)
        self._write_mdr1(BYTE_4 | EN_CNTR)

        # Set to zero at start
        self.counts = 0

    @property
    def counts(self):
        """Current counts as signed integer."""
        return self._get_counts()

    @counts.setter
    def counts(self, value):
        self._set_counts(value)

    @property
    def bits(self):
        """Counter bits."""
        return COUNTER_BITS[self._read_mdr1()[0] & 0x03]

    @bits.setter
    def bits(self, value):
        if value not in COUNTER_BITS:
            raise ValueError("Bits must be one of ", *COUNTER_BITS)
        self._write_mdr1(self._read_mdr1()[0] &0xFC | COUNTER_BITS.index(value))

    @property
    def quadrature(self):
        """Quadrature mode."""
        return QUADRATURE_MODES[self._read_mdr0()[0] & 0x03]

    @quadrature.setter
    def quadrature(self, value):
        if value not in QUADRATURE_MODES:
            raise ValueError("Mode must be one of ", *QUADRATURE_MODES)
        self._write_mdr0((self._read_mdr0()[0] & 0xFC) | QUADRATURE_MODES.index(value))

    def _get_counts(self, ):
        """Read the counter register value."""      
        bits = self.bits
        byte_values = self._read_cntr()
        counts = 0
        for b in byte_values:
            counts <<= 8
            counts |= b
        if counts >> (bits - 1):
            counts -= 1 << bits
        return counts

    def _set_counts(self, value):
        """Set the counter register value."""
        self._write_dtr(value)
        self._load_cntr()

    def _clear_mdr0(self):
        """Clear MDR0."""
        self._spi.writebytes([CLR_MDR0])

    def _clear_mdr1(self):
        """Clear MDR1."""
        self._spi.writebytes([CLR_MDR1])

    def _clear_cntr(self):
        """Clear the counter."""
        self._spi.writebytes([CLR_CNTR])

    def _clear_str(self):
        """Clear the status register."""
        self._spi.writebytes([CLR_STR])

    def _read_mdr0(self):
        """Read the 8 bit MDR0 register."""
        return self._spi.xfer2([READ_MDR0, 0x00])[1:]

    def _read_mdr1(self):
        """Read the 8 bit MDR1 register."""
        return self._spi.xfer2([READ_MDR1, 0x00])[1:]

    def _read_cntr(self):
        """Transfer CNTR to OTR, then read OTR. Size of return depends
           on current bit setting."""
        return self._spi.xfer2([READ_CNTR]+[0]*(self.bits//8))[1:]

    def _read_otr(self):
        """Output OTR."""
        return self._spi.xfer2([READ_OTR]+[0]*(self.bits//8))[1:]

    def _read_str(self):
        """Read 8 bit STR register."""
        return self._spi.xfer2([READ_STR,0x00])[1:]

    def _write_mdr0(self, mode):
        """Write serial data at MOSI into MDR0."""
        self._spi.writebytes([WRITE_MDR0, mode])

    def _write_mdr1(self, mode):
        """Write serial data at MOSI into MDR1."""
        self._spi.writebytes([WRITE_MDR1, mode])

    def _write_dtr(self, value):
        """Write to 32 bit DTR register."""
        self._spi.writebytes([WRITE_DTR, value >> 24 & 0xFF,
                                         value >> 16 & 0xFF,
                                         value >>  8 & 0xFF,
                                         value       & 0xFF])

    def _load_cntr(self):
        """Transfer DTR to CNTR."""
        self._spi.writebytes([LOAD_CNTR])

    def _load_otr(self):
        """Transfer CNTR to OTR."""
        self._spi.writebytes([LOAD_OTR])
