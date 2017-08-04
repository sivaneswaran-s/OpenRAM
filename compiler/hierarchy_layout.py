import itertools
import geometry
import gdsMill
import debug
from tech import drc, GDS
from tech import layer as techlayer
import os
from vector import vector
from pin_layout import pin_layout

class layout:
    """
    Class consisting of a set of objs and instances for a module
    This provides a set of useful generic types for hierarchy
    management. If a module is a custom designed cell, it will read from
    the GDS and spice files and perform LVS/DRC. If it is dynamically
    generated, it should implement a constructor to create the
    layout/netlist and perform LVS/DRC.
    """

    def __init__(self, name):            
        self.name = name
        self.width = None
        self.height = None
        self.insts = []      # Holds module/cell layout instances
        self.objs = []       # Holds all other objects (labels, geometries, etc)
        self.pin_map = {}    # Holds name->(vector,layer) map for all pins
        self.visited = False # Flag for traversing the hierarchy 

        self.gds_read()

    ############################################################
    # GDS layout
    ############################################################
    def offset_all_coordinates(self):
        """ This function is called after everything is placed to
        shift the origin in the lowest left corner """
        coordinate = self.find_lowest_coords()
        self.offset_attributes(coordinate)
        self.translate(coordinate)

    def get_gate_offset(self, x_offset, height, inv_num):
        """Gets the base offset and y orientation of stacked rows of gates
        assuming a minwidth metal1 vdd/gnd rail. Input is which gate
        in the stack from 0..n
        """

        if (inv_num % 2 == 0):
            base_offset=vector(x_offset, inv_num * height)
            y_dir = 1
        else:
            # we lose a rail after every 2 gates            
            base_offset=vector(x_offset, (inv_num+1) * height - (inv_num%2)*drc["minwidth_metal1"])
            y_dir = -1
            
        return (base_offset,y_dir)


    def find_lowest_coords(self):
        """Finds the lowest set of 2d cartesian coordinates within
        this layout"""
        #***1,000,000 number is used to avoid empty sequences errors***
        # FIXME Is this hard coded value ok??
        try:
            lowestx1 = min(rect.offset.x for rect in self.objs)
            lowesty1 = min(rect.offset.y for rect in self.objs)
        except:
            [lowestx1, lowesty1] = [1000000.0, 1000000.0]
        try:
            lowestx2 = min(inst.offset.x for inst in self.insts)
            lowesty2 = min(inst.offset.y for inst in self.insts)
        except:
            [lowestx2, lowesty2] = [1000000.0, 1000000.0]
        return vector(min(lowestx1, lowestx2), min(lowesty1, lowesty2))

    def offset_attributes(self, coordinate):
        """Translates all stored 2d cartesian coordinates within the
        attr dictionary"""
        # FIXME: This is dangerous. I think we should not do this, but explicitly
        # offset the necessary coordinates.

        #for attr_key, attr_val in self.attr.items():
        for attr_key in dir(self):
            attr_val = getattr(self,attr_key)

            # skip the list of things as these will be offset separately
            if (attr_key in ['objs','insts','mods','pins','conns','name_map']): continue

            # if is a list
            if isinstance(attr_val, list):
                
                for i in range(len(attr_val)):
                    # each unit in the list is a list coordinates
                    if isinstance(attr_val[i], (list,vector)):
                        attr_val[i] = vector(attr_val[i] - coordinate)
                    # the list itself is a coordinate
                    else:
                        if len(attr_val)!=2: continue
                        for val in attr_val:
                            if not isinstance(val, (int, long, float)): continue
                        setattr(self,attr_key, vector(attr_val - coordinate))
                        break

            # if is a vector coordinate
            if isinstance(attr_val, vector):
                setattr(self, attr_key, vector(attr_val - coordinate))



    def translate(self, coordinate):
        """Translates all 2d cartesian coordinates in a layout given
        the (x,y) offset"""
        for obj in self.objs:
            obj.offset = vector(obj.offset - coordinate)
        for inst in self.insts:
            inst.offset = vector(inst.offset - coordinate)

    def add_inst(self, name, mod, offset=[0,0], mirror="R0",rotate=0):
        """Adds an instance of a mod to this module"""
        self.insts.append(geometry.instance(name, mod, offset, mirror, rotate))
        debug.info(4, "adding instance" + ",".join(x.name for x in self.insts))
        return self.insts[-1]

    def add_rect(self, layer, offset, width, height):
        """Adds a rectangle on a given layer,offset with width and height"""
        # negative layers indicate "unused" layers in a given technology
        layerNumber = techlayer[layer]
        if layerNumber >= 0:
            self.objs.append(geometry.rectangle(layerNumber, offset, width, height))
        
                         
    def get_pin(self, text):
        """ Return the pin or list of pins """
        # If we have one pin, return it and not the list
        if len(self.pin_map[text])==1:
            return self.pin_map[text][0]
        # For multiple pins (e.g. vdd, gnd, return the list for iteration)
        return self.pin_map[text]
    
    def add_layout_pin(self, text, layer, offset, width=None, height=None):
        """Create a labeled pin"""
        if width==None:
            width=drc["minwidth_{0}".format(layer)]
        if height==None:
            height=drc["minwidth_{0}".format(layer)]
        self.add_rect(layer=layer,
                      offset=offset,
                      width=width,
                      height=height)
        self.add_label(text=text,
                       layer=layer,
                       offset=offset)
        
        try:
            self.pin_map[text].append(pin_layout(text,vector(offset,offset+vector(width,height)),layer))
        except KeyError:
            self.pin_map[text] = [pin_layout(text,vector(offset,offset+vector(width,height)),layer)]
                                      

    def add_label(self, text, layer, offset=[0,0],zoom=-1):
        """Adds a text label on the given layer,offset, and zoom level"""
        # negative layers indicate "unused" layers in a given technology
        layerNumber = techlayer[layer]
        if layerNumber >= 0:
            self.objs.append(geometry.label(text, layerNumber, offset, zoom))


    def add_path(self, layer, coordinates, width=None):
        """Connects a routing path on given layer,coordinates,width."""
        debug.info(3,"add path " + str(layer) + " " + str(coordinates))
        import path
        # NOTE: (UNTESTED) add_path(...) is currently not used
        # negative layers indicate "unused" layers in a given technology
        #layerNumber = techlayer[layer]
        #if layerNumber >= 0:
        #    self.objs.append(geometry.path(layerNumber, coordinates, width))

        path.path(obj=self,
                  layer=layer, 
                  position_list=coordinates, 
                  width=drc["minwidth_{}".format(layer)])

    def add_route(self, design, layers, coordinates):
        """Connects a routing path on given layer,coordinates,width. The
        layers are the (horizontal, via, vertical). add_wire assumes
        preferred direction routing whereas this includes layers in
        the coordinates.
        """
        import route
        debug.info(3,"add route " + str(layers) + " " + str(coordinates))
        # add an instance of our path that breaks down into rectangles and contacts
        route.route(obj=self,
                    layer_stack=layers, 
                    path=coordinates)

    
    def add_wire(self, layers, coordinates):
        """Connects a routing path on given layer,coordinates,width.
        The layers are the (horizontal, via, vertical). """
        import wire
        # add an instance of our path that breaks down into rectangles and contacts
        wire.wire(obj=self,
                  layer_stack=layers, 
                  position_list=coordinates)

    def add_contact(self, layers, offset, size=[1,1], mirror="R0", rotate=0):
        """ This is just an alias for a via."""
        return self.add_via(layers=layers,
                            offset=offset,
                            size=size,
                            mirror=mirror,rotate=rotate)

    def add_via(self, layers, offset, size=[1,1], mirror="R0", rotate=0):
        """ Add a three layer via structure. """
        import contact
        via = contact.contact(layer_stack=layers,
                              dimensions=size)
        self.add_mod(via)
        self.add_inst(name=via.name, 
                      mod=via, 
                      offset=offset,
                      mirror=mirror,
                      rotate=rotate)
        # We don't model the logical connectivity of wires/paths
        self.connect_inst([])
        return via

    def add_ptx(self, offset, mirror="R0", rotate=0, width=1, mults=1, tx_type="nmos"):
        """Adds a ptx module to the design."""
        import ptx
        mos = ptx.ptx(width=width,
                      mults=mults,
                      tx_type=tx_type)
        self.add_mod(mos)
        self.add_inst(name=mos.name, 
                      mod=mos, 
                      offset=offset,
                      mirror=mirror,
                      rotate=rotate)
        return mos


    def gds_read(self):
        """Reads a GDSII file in the library and checks if it exists
           Otherwise, start a new layout for dynamic generation."""
        # open the gds file if it exists or else create a blank layout
        if os.path.isfile(self.gds_file):
            debug.info(3, "opening %s" % self.gds_file)
            self.gds = gdsMill.VlsiLayout(units=GDS["unit"])
            reader = gdsMill.Gds2reader(self.gds)
            reader.loadFromFile(self.gds_file)
        else:
            debug.info(3, "creating structure %s" % self.name)
            self.gds = gdsMill.VlsiLayout(name=self.name, units=GDS["unit"])

    def print_gds(self, gds_file=None):
        """Print the gds file (not the vlsi class) to the terminal """
        if gds_file == None:
            gds_file = self.gds_file
        debug.info(3, "Printing %s" % gds_file)
        arrayCellLayout = gdsMill.VlsiLayout(units=GDS["unit"])
        reader = gdsMill.Gds2reader(arrayCellLayout, debugToTerminal=1)
        reader.loadFromFile(gds_file)

    def clear_visited(self):
        """ Recursively clear the visited flag """
        if not self.visited:
            for i in self.insts:
                i.mod.clear_visited()
        self.visited = False

    def gds_write_file(self, newLayout):
        """Recursive GDS write function"""
        if self.visited:
            return
        for i in self.insts:
            i.gds_write_file(newLayout)
        for i in self.objs:
            i.gds_write_file(newLayout)
        self.visited = True

    def gds_write(self, gds_name):
        """Write the entire gds of the object to the file."""
        debug.info(3, "Writing to {0}".format(gds_name))

        #self.gds = gdsMill.VlsiLayout(name=self.name,units=GDS["unit"])
        writer = gdsMill.Gds2writer(self.gds)
        # clear the visited flag for the traversal
        self.clear_visited()
        # recursively create all the remaining objects
        self.gds_write_file(self.gds)
        # populates the xyTree data structure for gds
        # self.gds.prepareForWrite()
        writer.writeToFile(gds_name)

    def pdf_write(self, pdf_name):
        # NOTE: Currently does not work (Needs further research)
        #self.pdf_name = self.name + ".pdf"
        debug.info(0, "Writing to %s" % pdf_name)
        pdf = gdsMill.pdfLayout(self.gds)

        return
        pdf.layerColors[self.gds.layerNumbersInUse[0]] = "#219E1C"
        pdf.layerColors[self.gds.layerNumbersInUse[1]] = "#271C9E"
        pdf.layerColors[self.gds.layerNumbersInUse[2]] = "#CC54C8"
        pdf.layerColors[self.gds.layerNumbersInUse[3]] = "#E9C514"
        pdf.layerColors[self.gds.layerNumbersInUse[4]] = "#856F00"
        pdf.layerColors[self.gds.layerNumbersInUse[5]] = "#BD1444"
        pdf.layerColors[self.gds.layerNumbersInUse[6]] = "#FD1444"
        pdf.layerColors[self.gds.layerNumbersInUse[7]] = "#FD1414"

        pdf.setScale(500)
        pdf.drawLayout()
        pdf.writeToFile(pdf_name)

    def print_attr(self):
        """Prints a list of attributes for the current layout object"""
        debug.info(0, 
                   "|==============================================================================|")
        debug.info(0, 
                   "|=========      LIST OF OBJECTS (Rects) FOR: " + self.attr["name"])
        debug.info(0, 
                   "|==============================================================================|")
        for obj in self.objs:
            debug.info(0, "layer={0} : offset={1} : size={2}".format(
                obj.layerNumber, obj.offset, obj.size))

        debug.info(0, 
                   "|==============================================================================|")
        debug.info(0, 
                   "|=========      LIST OF INSTANCES FOR: " +
                   self.attr["name"])
        debug.info(0, 
                   "|==============================================================================|")
        for inst in self.insts:
            debug.info(0, "name={0} : mod={1} : offset={2}".format(
                inst.name, inst.mod.name, inst.offset))
