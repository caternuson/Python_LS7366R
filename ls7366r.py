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

COUNTER_BITS = (32, 24, 16, 8)
QUADRATURE_MODES = (0, 1, 2, 4)

# Masks for the instruction register (IR)
REG_CLEAR   = 0x00
REG_READ    = 0x40
REG_WRITE   = 0x80
REG_LOAD    = 0xC0

REG_NONE    = 0x00
REG_MDR0    = 0x08  # Mode Register 0
REG_MDR1    = 0x10  # Mode Register 1
REG_DTR     = 0x18  # Data Register
REG_CNTR    = 0x20  # Counter Register
REG_OTR     = 0x28  # Output coutner Register
REG_STR     = 0x39  # Status Register

# Masks for Mode Register 0 (MDR0)
QUAD_X0     = 0x00  # non-quadrature count mode. (A = clock, B = direction)
QUAD_X1     = 0x01  # x1 quadrature count mode (one count per quadrature cycle)
QUAD_X2     = 0x02  # x2 quadrature count mode (two counts per quadrature cycle)
QUAD_X4     = 0x03  # x4 quadrature count mode (four counts per quadrature cycle)

CNT_FREE    = 0x00  # free-running count mode
CNT_SINGLE  = 0x04  # single-cycle count mode
CNT_LIMIT   = 0x08  # range-limit count mode
CNT_MODULO  = 0x0C  # modulo-n count mode

INDEX_DISABLE   = 0x00  # disable index
INDEX_LOAD_CNTR = 0x10  # configure index as the "load CNTR" input (transfers DTR to CNTR)
INDEX_RST_CNTR  = 0x20  # configure index as the "reset CNTR" input (clears CNTR to 0)
INDEX_LOAD_OTR  = 0x30  # configure index as the "load OTR" input (transfers CNTR to OTR)

INDEX_ASYNCH    = 0x00  # asynchronous index
INDEX_SYNCH     = 0x40  # synchronous index (overridden in non-quadrature mode)

FILTER_1    = 0x00  # filter clock division factor = 1
FILTER_2    = 0x80  # filter clock division factor = 2

# Masks for Mode Register 1 (MDR1)
CNTR_ENABLE     = 0x00  # enable counting
CNTR_DISABLE    = 0x04  # disable counting

CNTR_4_BYTE = 0x00  # 4-byte counter mode
CNTR_3_BYTE = 0x01  # 3-byte counter mode
CNTR_2_BYTE = 0x02  # 2-byte counter mode
CNTR_1_BYTE = 0x03  # 1-byte counter mode

FLAG_NONE   = 0x00  # FLAGs disabled
FLAG_IDX    = 0x10  # FLAG on IDX (B4 of STR)
FLAG_CMP    = 0x20  # FLAG on CMP (B5 of STR)
FLAG_BW     = 0x40  # FLAG on BW (B6 of STR)
FLAG_CY     = 0x80  # FLAG on CY (B7 of STR)

# Masks for Status Register (STR)
STR_SIGN    = 0x01  # Sign bit. 1: negative, 0: positive
STR_DIR     = 0x02  # Count direction indicator: 0: count down, 1: count up
STR_PLS     = 0x04  # Power loss indicator latch; set upon power up
STR_CEN     = 0x08  # Count enable status: 0: counting disabled, 1: counting enabled
STR_IDX     = 0x10  # Index latch
STR_CMP     = 0x20  # Compare (CNTR = DTR) latch
STR_BW      = 0x40  # Borrow (CNTR underflow) latch
STR_CY      = 0x80  # Carry (CNTR overflow) latch


class LS7366R():
    """LSI/CSI LS7366R quadrature counter."""

    def __init__(self, spi):
        # This should be a SpiDev or compatible object.
        self._spi = spi

    @property
    def counts(self):
        """Current counts as signed integer."""
        bits = self.bits
        counts = self._read_register(REG_CNTR)
        # convert 2s comp to signed int
        counts = counts - (1 << bits) if counts >> (bits - 1) else counts  
        return counts

    @counts.setter
    def counts(self, value):
        self._write_register(REG_DTR, value)
        self._load_register(REG_CNTR)

    @property
    def bits(self):
        """Counter bits."""
        return COUNTER_BITS[self._read_register(REG_MDR1) & 0x03]

    @bits.setter
    def bits(self, value):
        if value not in COUNTER_BITS:
            raise ValueError("Bits must be one of ", *COUNTER_BITS)
        other_stuff = self._read_register(REG_MDR1) & 0xFC
        self._write_register(REG_MDR1, other_stuff | COUNTER_BITS.index(value))

    @property
    def quadrature(self):
        """Quadrature mode."""
        return QUADRATURE_MODES[self._read_register(REG_MDR0) & 0x03]

    @quadrature.setter
    def quadrature(self, value):
        if value not in QUADRATURE_MODES:
            raise ValueError("Mode must be one of ", *QUADRATURE_MODES)
        other_stuff = self._read_register(REG_MDR0) & 0xFC
        self._write_register(REG_MDR0, other_stuff | QUADRATURE_MODES.index(value))

    @property
    def enabled(self):
        """Counting state."""
        return bool(not self._read_register(REG_MDR1) & 0x04)

    @enabled.setter
    def enabled(self, state):
        other_stuff = self._read_register(REG_MDR1) & 0xFB
        self._write_register(REG_MDR1, other_stuff | int(not state)<<2)

    def _write_register(self, reg, value):
        reg_bytes = []
        for _ in range(self._sizeof_register(reg)):
            reg_bytes.append(value & 0xFF)
            value >>= 8
        reg_bytes.reverse()
        self._spi.writebytes([REG_WRITE | reg] + reg_bytes)
    
    def _read_register(self, reg):
        reg_bytes = self._spi.xfer2([REG_READ | reg]+[0]*self._sizeof_register(reg))
        value = 0
        for b in reg_bytes:
            value <<= 8
            value |= b
        return value        

    def _load_register(self, reg):
        self._spi.writebytes([REG_LOAD | reg])

    def _clear_register(self, reg):
        self._spi.writebytes([REG_CLEAR | reg])

    def _sizeof_register(self, reg):
        if reg in (REG_DTR, REG_CNTR, REG_OTR):
            return self.bits // 8
        else:
            return 1