from math import log
import design
from tech import drc
import debug
from vector import vector
from globals import OPTS

class write_driver_array(design.design):
    """
    Array of tristate drivers to write to the bitlines through the column mux.
    Dynamically generated write driver array of all bitlines.
    """

    def __init__(self, columns, word_size):
        design.design.__init__(self, "write_driver_array")
        debug.info(1, "Creating {0}".format(self.name))

        c = reload(__import__(OPTS.config.write_driver))
        self.mod_write_driver = getattr(c, OPTS.config.write_driver)
        self.driver = self.mod_write_driver("write_driver")
        self.add_mod(self.driver)

        self.columns = columns
        self.word_size = word_size
        self.words_per_row = columns / word_size

        self.width = self.columns * self.driver.width
        self.height = self.height = self.driver.height
        
        self.add_pins()
        self.create_layout()
        self.DRC_LVS()

    def add_pins(self):
        for i in range(0,self.columns,self.words_per_row):
            self.add_pin("data[{0}]".format(i/self.words_per_row))
        for i in range(0,self.columns,self.words_per_row):
            self.add_pin("bl[{0}]".format(i))
        for i in range(0,self.columns,self.words_per_row):
            self.add_pin("br[{0}]".format(i))
        self.add_pin("wen")
        self.add_pin("vdd")
        self.add_pin("gnd")

    def create_layout(self):
        self.create_write_array()
        self.add_layout_pins()
        #self.offset_all_coordinates()

    def create_write_array(self):
        for i in range(0,self.columns,self.words_per_row):
            name = "Xwrite_driver%d".format(i)
            x_off = i*self.driver.width
            self.add_inst(name=name,
                          mod=self.driver,
                          offset=[x_off, 0])
            self.connect_inst(["data[{0}]".format(i/self.words_per_row),
                               "bl[{0}]".format(i),
                               "br[{0}]".format(i),
                               "wen", "vdd", "gnd"])


    def add_layout_pins(self):
        bl_pin = self.driver.get_pin("BL")            
        br_pin = self.driver.get_pin("BR")
        din_pin = self.driver.get_pin("din")
        
        for i in range(0,self.columns,self.words_per_row):
            base = vector(i*self.driver.width, 0)

            bl_offset = base + bl_pin.ll()
            br_offset = base + br_pin.ll()
            din_offset = base + din_pin.ll()
            

            self.add_layout_pin(text="data_in[{0}]".format(i),
                                layer="metal2",
                                offset=din_offset,
                                width=din_pin.width(),
                                height=din_pin.height())
            self.add_layout_pin(text="bl[{0}]".format(i),
                                layer="metal2",
                                offset=bl_offset,
                                width=bl_pin.width(),
                                height=bl_pin.height())
                           
            self.add_layout_pin(text="br[{0}]".format(i),
                                layer="metal2",
                                offset=br_offset,
                                width=br_pin.width(),
                                height=br_pin.height())
                           

        self.add_layout_pin(text="wen",
                            layer="metal1",
                            offset=self.driver.get_pin("en").ll().scale(0,1),
                            width=self.width - (self.words_per_row - 1) * self.driver.width,
                            height=drc['minwidth_metal1'])
                       
        self.add_layout_pin(text="vdd",
                            layer="metal1",
                            offset=self.driver.get_pin("vdd").ll().scale(0,1),
                            width=self.width,
                            height=drc['minwidth_metal1'])
                       
        self.add_layout_pin(text="gnd",
                            layer="metal1",
                            offset=self.driver.get_pin("gnd").ll().scale(0,1),
                            width=self.width,
                            height=drc['minwidth_metal1'])
                       

