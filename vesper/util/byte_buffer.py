"""Module containing `ByteBuffer` class."""


import numbers
import struct


class ByteBuffer:
    
    """Buffer supporting formatted binary writes and reads."""
    
    
    def __init__(self, arg):
        
        if isinstance(arg, numbers.Integral):
            self.bytes = bytearray(arg)
        else:
            self.bytes = arg
            
        self.offset = 0
        
        
    def write_bytes(self, bytes_, offset=None):

        if offset is not None:
            self.offset = offset
            
        size = len(bytes_)
        
        self.bytes[self.offset:self.offset + size] = bytes_
        
        self.offset += size
    
        
    def write_value(self, value, format_, offset=None):
        
        if offset is not None:
            self.offset = offset
            
        struct.pack_into(format_, self.bytes, self.offset, value)
            
        self.offset += struct.calcsize(format_)
        
        
    def read_bytes(self, size, offset=None):
        
        if offset is not None:
            self.offset = offset
            
        bytes_ = self.bytes[self.offset:self.offset + size]
        
        self.offset += size
        
        return bytes_
            
    
    def read_value(self, format_, offset=None):
        
        if offset is not None:
            self.offset = offset
            
        value = struct.unpack_from(format_, self.bytes, self.offset)[0]
        
        self.offset += struct.calcsize(format_)
        
        return value
