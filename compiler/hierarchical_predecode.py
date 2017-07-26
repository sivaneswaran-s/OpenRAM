import debug
import design
import math
from tech import drc
from contact import contact
from pinv import pinv
from vector import vector
from globals import OPTS
from nand_2 import nand_2
from nand_3 import nand_3


class hierarchical_predecode(design.design):
    """
    Pre 2x4 and 3x8 decoder shared code.
    """
    def __init__(self, input_number):
        self.number_of_inputs = input_number
        self.number_of_outputs = int(math.pow(2, self.number_of_inputs))
        design.design.__init__(self, name="pre{0}x{1}".format(self.number_of_inputs,self.number_of_outputs))

        c = reload(__import__(OPTS.config.bitcell))
        self.mod_bitcell = getattr(c, OPTS.config.bitcell)
        self.bitcell_height = self.mod_bitcell.height

    
    def add_pins(self):
        for k in range(self.number_of_inputs):
            self.add_pin("in[{0}]".format(k))
        for i in range(self.number_of_outputs):
            self.add_pin("out[{0}]".format(i))
        self.add_pin("vdd")
        self.add_pin("gnd")

    def create_modules(self):
        """ Create the INV and NAND gate """
        
        self.inv = pinv()
        self.add_mod(self.inv)
        
        self.create_nand(self.number_of_inputs)
        self.add_mod(self.nand)

    def create_nand(self,inputs):
        """ Create the NAND for the predecode input stage """
        if inputs==2:
            self.nand = nand_2()
        elif inputs==3:
            self.nand = nand_3()
        else:
            debug.error("Invalid number of predecode inputs.",-1)
            
    def setup_constraints(self):
        self.m1m2_via = contact(layer_stack=("metal1", "via1", "metal2")) 
        self.metal2_space = drc["metal2_to_metal2"]
        self.metal1_space = drc["metal1_to_metal1"]
        self.metal2_width = drc["minwidth_metal2"]
        self.metal1_width = drc["minwidth_metal1"]
        # we are going to use horizontal vias, so use the via height
        # use a conservative douple spacing just to get rid of annoying via DRCs
        self.metal2_pitch = self.m1m2_via.height + 2*self.metal2_space
        # This is to shift the rotated vias to be on m2 pitch
        self.via_x_shift = self.m1m2_via.height + self.m1m2_via.via_layer_position.scale(0,-1).y
        # This is to shift the via if the metal1 and metal2 overlaps are different
        self.via_y_shift = self.m1m2_via.second_layer_position.x - self.m1m2_via.first_layer_position.x + self.m1m2_via.via_layer_position.scale(-0.5,0).x
        
        # The rail offsets are indexed by the label
        self.rails = {}

        # Non inverted input rails
        for rail_index in range(self.number_of_inputs):
            xoffset = rail_index * self.metal2_pitch
            self.rails["in[{}]".format(rail_index)]=xoffset
        # x offset for input inverters
        self.x_off_inv_1 = self.number_of_inputs*self.metal2_pitch 
        
        # Creating the right hand side metal2 rails for output connections
        for rail_index in range(2 * self.number_of_inputs + 2):
            xoffset = self.x_off_inv_1 + self.inv.width + ((rail_index+1) * self.metal2_pitch)
            if rail_index == 0:
                self.rails["vdd"]=xoffset
            elif rail_index == 1:
                self.rails["gnd"]=xoffset
            elif rail_index < 2+self.number_of_inputs:
                self.rails["Abar[{}]".format(rail_index-2)]=xoffset
            else:
                self.rails["A[{}]".format(rail_index-self.number_of_inputs-2)]=xoffset

        # x offset to NAND decoder includes the left rails, mid rails and inverters, plus an extra m2 pitch
        self.x_off_nand = self.x_off_inv_1 + self.inv.width + (3 + 2*self.number_of_inputs) * self.metal2_pitch

                       
        # x offset to output inverters
        self.x_off_inv_2 = self.x_off_nand + self.nand.width

        # Height width are computed 
        self.width = self.x_off_inv_2 + self.inv.width
        self.height = self.number_of_outputs * self.nand.height

    def create_rails(self):
        """ Create all of the rails for the inputs and vdd/gnd/inputs_bar/inputs """
        for label in self.rails.keys():
            # these are not primary inputs, so they shouldn't have a
            # label or LVS complains about different names on one net
            if label.startswith("in"):
                self.add_layout_pin(text=label,
                                    layer="metal2",
                                    offset=[self.rails[label], 0], 
                                    width=self.metal2_width,
                                    height=self.height)
            else:
                self.add_rect(layer="metal2",
                              offset=[self.rails[label], 0], 
                              width=self.metal2_width,
                              height=self.height)
                # label for convenience, it is not a pin
                self.add_label(text=label,
                               layer="metal2",
                               offset=[self.rails[label], 0])

    def add_input_inverters(self):
        """ Create the input inverters to invert input signals for the decode stage. """
        for inv_num in range(self.number_of_inputs):
            name = "Xpre_inv[{0}]".format(inv_num)
            if (inv_num % 2 == 0):
                y_off = inv_num * (self.inv.height)
                offset = vector(self.x_off_inv_1, y_off)
                mirror = "R0"
            else:
                y_off = (inv_num + 1) * (self.inv.height)
                offset = vector(self.x_off_inv_1, y_off)
                mirror="MX"
            self.add_inst(name=name,
                          mod=self.inv,
                          offset=offset,
                          mirror=mirror)
            self.connect_inst(["in[{0}]".format(inv_num),
                               "inbar[{0}]".format(inv_num),
                               "vdd", "gnd"])
            
    def add_output_inverters(self):
        """ Create inverters for the inverted output decode signals. """
        
        self.decode_out_positions = []
        z_pin = self.inv.get_pin("Z")
        for inv_num in range(self.number_of_outputs):
            name = "Xpre2x4_nand_inv[{}]".format(inv_num)
            if (inv_num % 2 == 0):
                y_factor = inv_num
                mirror = "R0"
                y_dir = 1
            else:
                y_factor =inv_num + 1
                mirror = "MX"
                y_dir = -1
            base = vector(self.x_off_inv_2, self.inv.height * y_factor)   
            self.add_inst(name=name,
                          mod=self.inv,
                          offset=base,
                          mirror=mirror)
            self.connect_inst(["Z[{}]".format(inv_num),
                               "out[{}]".format(inv_num),
                               "vdd", "gnd"])
            
            z_pin = self.inv.get_pin("Z")
            self.add_layout_pin(text="out[{}]".format(inv_num),
                                layer="metal1",
                                offset=base+z_pin.ll().scale(1,y_dir),
                                width=z_pin.width(),
                                height=z_pin.height()*y_dir)
            

    def add_nand(self,connections):
        """ Create the NAND stage for the decodes """
        z_pin = self.nand.get_pin("Z")
        a_pin = self.inv.get_pin("A")
        for nand_input in range(self.number_of_outputs):
            inout = str(self.number_of_inputs)+"x"+str(self.number_of_outputs)
            name = "Xpre{0}_nand[{1}]".format(inout,nand_input)
            rect_height = z_pin.uy()-a_pin.ly()
            if (nand_input % 2 == 0):
                y_off = nand_input * (self.nand.height)
                mirror = "R0"
                rect_offset = vector(self.x_off_nand + self.nand.width,
                                     y_off + z_pin.uy() - rect_height)
            else:
                y_off = (nand_input + 1) * (self.nand.height)
                mirror = "MX"
                rect_offset =vector(self.x_off_nand + self.nand.width,
                                    y_off - z_pin.uy())
            self.add_inst(name=name,
                          mod=self.nand,
                          offset=[self.x_off_nand, y_off],
                          mirror=mirror)
            self.add_rect(layer="metal1",
                          offset=rect_offset,
                          width=self.metal1_width,
                          height=rect_height)
            self.connect_inst(connections[nand_input])

    def route(self):
        self.route_input_inverters()
        self.route_inputs_to_rails()
        self.route_nand_to_rails()
        self.route_vdd_gnd_from_rails()

    def route_inputs_to_rails(self):
        """ Route the uninverted inputs to the second set of rails """
        for num in range(self.number_of_inputs):
            # route one signal next to each vdd/gnd rail since this is
            # typically where the p/n devices are and there are no
            # pins in the nand gates. 
            y_offset = (num+self.number_of_inputs) * self.inv.height + 2*self.metal1_space
            in_pin = "in[{}]".format(num)            
            a_pin = "A[{}]".format(num)            
            self.add_rect(layer="metal1",
                          offset=[self.rails[in_pin],y_offset],
                          width=self.rails[a_pin] + self.metal2_width - self.rails[in_pin],
                          height=self.metal1_width)
            self.add_via(layers = ("metal1", "via1", "metal2"),
                         offset=[self.rails[in_pin] + self.via_x_shift, y_offset + self.via_y_shift],
                         rotate=90)
            self.add_via(layers = ("metal1", "via1", "metal2"),
                         offset=[self.rails[a_pin] + self.via_x_shift, y_offset + self.via_y_shift],
                         rotate=90)
            
    def route_input_inverters(self):
        """
        Route all conections of the inputs inverters [Inputs, outputs, vdd, gnd] 
        """
        for inv_num in range(self.number_of_inputs):
            (inv_offset, y_dir) = self.get_gate_offset(self.x_off_inv_1, self.inv.height, inv_num)
            
            out_pin = "Abar[{}]".format(inv_num)
            in_pin = "in[{}]".format(inv_num)
            
            #add output so that it is just below the vdd or gnd rail
            # since this is where the p/n devices are and there are no
            # pins in the nand gates.
            y_offset = (inv_num+1) * self.inv.height - 3*self.metal1_space
            inv_out_offset = inv_offset+self.inv.get_pin("Z").ur().scale(1,y_dir)-vector(0,self.metal1_width).scale(1,y_dir)
            self.add_rect(layer="metal1",
                          offset=[inv_out_offset.x,y_offset],
                          width=self.rails[out_pin]-inv_out_offset.x + self.metal2_width,
                          height=self.metal1_width)
            self.add_rect(layer="metal1",
                          offset=inv_out_offset,
                          width=self.metal1_width,
                          height=y_offset-inv_out_offset.y)
            self.add_via(layers = ("metal1", "via1", "metal2"),
                         offset=[self.rails[out_pin] + self.via_x_shift, y_offset + self.via_y_shift],
                         rotate=90)

            
            #route input
            inv_in_offset = inv_offset+self.inv.get_pin("A").ll().scale(1,y_dir)
            self.add_rect(layer="metal1",
                          offset=[self.rails[in_pin], inv_in_offset.y],
                          width=inv_in_offset.x - self.rails[in_pin],
                          height=self.metal1_width)
            self.add_via(layers=("metal1", "via1", "metal2"),
                         offset=[self.rails[in_pin] +  self.via_x_shift, inv_in_offset.y + self.via_y_shift],
                         rotate=90)
            


    def get_gate_offset(self, x_offset, height, inv_num):
        """ Gets the base offset and y orientation of stacked rows of gates.
        Input is which gate in the stack from 0..n
        """

        if (inv_num % 2 == 0):
            base_offset=vector(x_offset, inv_num * height)
            y_dir = 1
        else:
            # we lose a rail after every 2 gates            
            base_offset=vector(x_offset, (inv_num+1) * height - (inv_num%2)*self.metal1_width)
            y_dir = -1
            
        return (base_offset,y_dir)

    

    def route_nand_to_rails(self):
        # This 2D array defines the connection mapping 
        nand_input_line_combination = self.get_nand_input_line_combination()
        for k in range(self.number_of_outputs):
            # create x offset list         
            index_lst= nand_input_line_combination[k]
            (nand_offset,y_dir) = self.get_gate_offset(self.x_off_nand,self.nand.height,k)

            if self.number_of_inputs == 2:
                gate_lst = ["A","B"]
            else:
                gate_lst = ["A","B","C"]                

            # this will connect pins A,B or A,B,C
            for rail_pin,gate_pin in zip(index_lst,gate_lst):
                pin_offset = nand_offset+self.nand.get_pin(gate_pin).ll().scale(1,y_dir)                
                self.add_rect(layer="metal1",
                              offset=[self.rails[rail_pin], pin_offset.y],
                              width=pin_offset.x - self.rails[rail_pin],
                              height=self.metal1_width)
                self.add_via(layers=("metal1", "via1", "metal2"),
                             offset=[self.rails[rail_pin] +  self.via_x_shift, pin_offset.y + self.via_y_shift],
                             rotate=90)



    def route_vdd_gnd_from_rails(self):
        """All the vdd and gnd are connected internally, so this just creates
        a vdd/gnd rail at the top and bottom."""

        for num in range(0,self.number_of_outputs):
            # this will result in duplicate polygons for rails, but who cares
            
            # use the inverter offset even though it will be the nand's too
            (gate_offset, y_dir) = self.get_gate_offset(0, self.inv.height, num)

            # route vdd
            vdd_offset = gate_offset + self.inv.get_pin("vdd").ll().scale(1,y_dir) 
            self.add_layout_pin(text="vdd",
                                layer="metal1",
                                offset=vdd_offset,
                                width=self.x_off_inv_2 + self.inv.width + self.metal2_width,
                                height=self.metal1_width)
            self.add_via(layers = ("metal1", "via1", "metal2"),
                         offset=[self.rails["vdd"] +  self.via_x_shift, vdd_offset.y + self.via_y_shift],
                         rotate=90)

            # route gnd
            gnd_offset = gate_offset+self.inv.get_pin("gnd").ll().scale(1,y_dir)
            self.add_layout_pin(text="gnd",
                                layer="metal1",
                                offset=gnd_offset,
                                width=self.x_off_inv_2 + self.inv.width + self.metal2_width,
                                height=self.metal1_width)
            self.add_via(layers = ("metal1", "via1", "metal2"),
                         offset=[self.rails["gnd"] +  self.via_x_shift, gnd_offset.y + self.via_y_shift],
                         rotate=90)
        


