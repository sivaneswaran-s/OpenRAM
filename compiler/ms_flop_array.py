import debug
import design
from tech import drc
from math import log
from vector import vector
from globals import OPTS

class ms_flop_array(design.design):
    """
    An Array of D-Flipflops used for to store Data_in & Data_out of
    Write_driver & Sense_amp, address inputs of column_mux &
    hierdecoder
    """

    def __init__(self, columns, word_size, name=""):
        self.columns = columns
        self.word_size = word_size
        if name=="":
            name = "flop_array_c{0}_w{1}".format(columns,word_size)
        design.design.__init__(self, name)
        debug.info(1, "Creating %s".format(self.name))

        c = reload(__import__(OPTS.config.ms_flop))
        self.mod_ms_flop = getattr(c, OPTS.config.ms_flop)
        self.ms = self.mod_ms_flop("ms_flop")
        self.add_mod(self.ms)

        self.width = self.columns * self.ms.width
        self.height = self.ms.height
        self.words_per_row = self.columns / self.word_size

        self.create_layout()

    def create_layout(self):
        self.add_modules()
        self.setup_layout_constants()
        self.add_pins()
        self.create_ms_flop_array()
        self.add_layout_pins()
        self.DRC_LVS()

    def add_pins(self):
        for i in range(self.word_size):
            self.add_pin("din[{0}]".format(i))
            self.add_pin("dout[{0}]".format(i))
            self.add_pin("dout_bar[{0}]".format(i))
        self.add_pin("clk")
        self.add_pin("vdd")
        self.add_pin("gnd")

    def create_ms_flop_array(self):
        for i in range(self.word_size):
            name = "Xdff{0}".format(i)
            if (i % 2 == 0 or self.words_per_row>1):
                x_off = i * self.ms.width * self.words_per_row
                mirror = "R0"
            else:
                if (self.words_per_row == 1):
                    x_off = (i + 1) * self.ms.width
                    mirror="MY"
                else:
                    x_off = i * self.ms.width * self.words_per_row
            self.add_inst(name=name,
                          mod=self.ms,
                          offset=[x_off, 0], 
                          mirror=mirror)
            self.connect_inst(["din[{0}]".format(i),
                               "dout[{0}]".format(i),
                               "dout_bar[{0}]".format(i),
                               "clk",
                               "vdd", "gnd"])

    def add_layout_pins(self):
        
        offsets = {}
        for i in range(self.word_size):
            i_str = "[{0}]".format(i)
            if (i % 2 == 0 or self.words_per_row > 1):
                base = vector(i * self.ms.width * self.words_per_row, 0)
                x_dir = 1
            else:
                base = vector((i + 1) * self.ms.width, 0)
                x_dir = -1

            gnd_pin = self.ms.get_pin("gnd")
            # this name is not indexed so that it is a must-connect at next hierarchical level
            # it is connected by abutting the bitcell array
            self.add_layout_pin(text="gnd",
                                layer="metal2",
                                offset=base + gnd_pin.ll().scale(x_dir,1),
                                width=gnd_pin.width(),
                                height=gnd_pin.height())

            for p in ["din", "dout", "dout_bar"]:
                cur_pin = self.ms.get_pin(p)                
                self.add_layout_pin(text=p+i_str,
                                    layer="metal2",
                                    offset=base + cur_pin.ll().scale(x_dir,1),
                                    width=cur_pin.width(),
                                    height=cur_pin.height())

            
        # Continous "clk" rail along with label.
        self.add_layout_pin(text="clk",
                            layer="metal1",
                            offset=self.ms.get_pin("clk").ll().scale(0,1),
                            width=self.width,
                            height=drc["minwidth_metal1"])

        # Continous "Vdd" rail along with label.
        self.add_layout_pin(text="vdd",
                            layer="metal1",
                            offset=self.ms.get_pin("vdd").ll().scale(0,1),
                            width=self.width,
                            height=drc["minwidth_metal1"])


    def delay(self, slew, load=0.0):
        result = self.ms.delay(slew = slew, 
                               load = load)
        return result
