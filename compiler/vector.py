import debug


class vector():
    """
    This is the vector class to represent the coordinate
    vector. It makes the coordinate operations easy and short
    so the code is concise.
    It needs to override several operators to support
    concise vector operations, output, and other more complex
    data structures like lists.
    """
    def __init__(self, x, y=None):
        """ init function support two init method"""
        # will take single input as a coordinate
        if y==None:
            self.x = x[0]
            self.y = x[1]
        #will take two inputs as the values of a coordinate
        else:
            self.x = x
            self.y = y

    def __str__(self):
        """ override print function output """
        return "vector:["+str(self.x)+", "+str(self.y)+"]"

    def __repr__(self):
        """ override print function output """
        return "["+str(self.x)+", "+str(self.y)+"]"

    def __setitem__(self, index, value):
        """ 
        override setitem function 
        can set value by vector[index]=value
        """
        if index==0:
            self.x=value
        elif index==1:
            self.y=value
        else:
            self.x=value[0]
            self.y=value[1] 

    def __getitem__(self, index):
        """
        override getitem function 
        can get value by value=vector[index]
        """
        if index==0:
            return self.x
        elif index==1:
            return self.y
        else:
            return self                

    def __add__(self, other):
        """
        Override + function (left add)
        Can add by vector(x1,y1)+vector(x2,y2)
        """
        return vector(self.x + other[0], self.y + other[1])

    def __radd__(self, other):
        """
        Override + function (right add)
        """
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other):
        """
        Override - function (left)
        """
        return vector(self.x - other[0], self.y - other[1])

    def __rsub__(self, other):
        """
        Override - function (right)
        """
        return vector(other[0]- self.x, other[1] - self.y)

    def rotate(self):
        """ pass a copy of rotated vector, without altering the vector! """
        return vector(self.y,self.x)

    def scale(self, x_factor, y_factor=None):
        """ pass a copy of scaled vector, without altering the vector! """
        if y_factor==None:
            y_factor=x_factor[1]
            x_factor=x_factor[0]
        return vector(self.x*x_factor,self.y*y_factor)

    def rotate_scale(self, x_factor, y_factor=None):
        """ pass a copy of scaled vector, without altering the vector! """
        if y_factor==None:
            y_factor=x_factor[1]
            x_factor=x_factor[0]
        return vector(self.y*x_factor,self.x*y_factor)
