# Created by G. Peter Lepage (Cornell University) on 2012-05-31.
# Copyright (c) 2012 G. Peter Lepage. 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version (see <http://www.gnu.org/licenses/>).
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import collections
import numpy
import copy
import pickle
import gvar as _gvar

## BufferDict ##
BUFFERDICTDATA = collections.namedtuple('BUFFERDICTDATA',['slice','shape'])
""" Data type for BufferDict._data[k]. Note shape==None implies a scalar. """
    
class BufferDict(collections.MutableMapping):
    """ Dictionary whose data is packed into a 1-d buffer (numpy.array).
        
    A |BufferDict| object is a dictionary-like object whose values must either
    be scalars or arrays (like :mod:`numpy` arrays, with arbitrary shapes). 
    The scalars and arrays are assembled into different parts of a single 
    one-dimensional buffer. The various scalars and arrays are retrieved 
    using keys, as in a dictionary: *e.g.*,
        
        >>> a = BufferDict()
        >>> a['scalar'] = 0.0
        >>> a['vector'] = [1.,2.]
        >>> a['tensor'] = [[3.,4.],[5.,6.]]
        >>> print(a.flatten())              # print a's buffer
        [ 0.  1.  2.  3.  4.  5.  6.]
        >>> for k in a:                     # iterate over keys in a
        ...     print(k,a[k])
        scalar 0.0
        vector [ 1.  2.]
        tensor [[ 3.  4.]
         [ 5.  6.]]
        >>> a['vector'] = a['vector']*10    # change the 'vector' part of a
        >>> print(a.flatten())
        [  0.  10.  20.   3.   4.   5.   6.]
        
    The first four lines here could have been collapsed to one statement::
        
        a = BufferDict(scalar=0.0,vector=[1.,2.],tensor=[[3.,4.],[5.,6.]])
        
    or ::
        
        a = BufferDict([('scalar',0.0),('vector',[1.,2.]),
                        ('tensor',[[3.,4.],[5.,6.]])])
        
    where in the second case the order of the keys is preserved in ``a`` (that 
    is, ``BufferDict`` is an ordered dictionary).
        
    The keys and associated shapes in a |BufferDict| can be transferred to a
    different buffer, creating a new |BufferDict|: *e.g.*, using ``a`` from
    above,
        
        >>> buf = numpy.array([0.,10.,20.,30.,40.,50.,60.])
        >>> b = BufferDict(a,buf=buf)       # clone a but with new buffer
        >>> print(b['tensor'])
        [[ 30.  40.]
         [ 50.  60.]]
        >>> b['scalar'] += 1
        >>> print(buf)
        [  1.  10.  20.  30.  40.  50.  60.]
        
    Note how ``b`` references ``buf`` and can modify it. One can also replace
    the buffer in the original |BufferDict| using, for example, 
    ``a.flat = buf``:
        
        >>> a.flat = buf
        >>> print(a['tensor'])
        [[ 30.  40.]
         [ 50.  60.]]
        
    ``a.flat`` is an iterator for the ``numpy`` array used for ``a``'s buffer.
    It can be used to access and change the buffer directly. ``a.flatten()``
    is a copy of the buffer.
         
    A |BufferDict| functions like a dictionary except: a) items cannot be
    deleted once inserted; b) all values must be either scalars or
    (:mod:`numpy`) arrays of scalars, where the scalars can be any noniterable
    type that works with :mod:`numpy` arrays; and c) any new value assigned to a
    key must have the same size and shape as the original value.
        
    Note that |BufferDict|\s can be pickled and unpickled even when they 
    store |GVar|\s (which themselves cannot be pickled separately).
    """
    def __init__(self,*args,**kargs):
        super(BufferDict, self).__init__()
        self.shape = None
        if len(args)==0:
            ## kargs are dictionary entries ##
            self._buf = numpy.array([],int)
            self._keys = []
            self._data = {}
            for k in sorted(kargs):
                self[k] = kargs[k]
            ##
        else:
            if len(args)==2 and len(kargs)==0:
                bd,buf = args
            elif len(args)==1 and len(kargs)==0:
                bd = args[0]
                buf = None
            elif len(args)==1 and 'buf' in kargs and len(kargs)==1:
                bd = args[0]
                buf = kargs['buf']
            else:
                raise ValueError("Bad arguments for BufferDict.")
            if isinstance(bd,BufferDict):
                ## make copy of BufferDict bd, possibly with new buffer ##
                self._keys = copy.copy(bd._keys)
                self._data = copy.copy(bd._data)
                self._buf = numpy.array(bd._buf) if buf is None else numpy.asarray(buf)
                if bd.size!=self.size:
                    raise ValueError("buf is wrong size: "+str(self.size)+" not "
                                        +str(bd.size))
                if self._buf.ndim!=1:
                    raise ValueError("buf must be 1-d: "+str(self._buf.shape))
                ##
            elif buf is None:
                self._buf = numpy.array([],int)
                self._keys = []
                self._data = {}
                ## add initial data ## 
                if hasattr(bd,"keys"):
                    ## bd a dictionary ##
                    for k in sorted(bd):
                        self[k] = bd[k]
                    ##
                else:
                    ## bd an array of tuples ##
                    if not all([(isinstance(bdi,tuple) and len(bdi)==2) for bdi in bd]):
                        raise ValueError("BufferDict argument must be dict or list of 2-tuples.")
                    for ki,vi in bd:
                        self[ki] = vi
                    ##
                ##
            else:
                raise ValueError("bd must be a BufferDict in BufferDict(bd,buf): "
                                    +str(bd.__class__))
    ##
    def __getstate__(self):
        """ Capture state for pickling when elements are GVars. """
        if len(self._buf)<1:
            return self.__dict__.copy()
        odict = self.__dict__.copy()
        if isinstance(self._buf[0],_gvar.GVar):
            buf = odict['_buf']
            del odict['_buf']
            odict['_buf.mean'] = _gvar.mean(buf)
            odict['_buf.cov'] = _gvar.evalcov(buf)
        data = odict['_data']
        del odict['_data']
        odict['_data.tuple'] = {}
        for k in data:
            odict['_data.tuple'][k] = (data[k].slice,data[k].shape)
        return odict
    ##
    def __setstate__(self,odict):
        """ Restore state when unpickling when elements are GVars. """
        if '_buf.mean' in odict:
            buf = _gvar.gvar(odict['_buf.mean'],odict['_buf.cov'])
            del odict['_buf.mean']
            del odict['_buf.cov']
            odict['_buf'] = buf
        if '_data.tuple' in odict:
            data = odict['_data.tuple']
            del odict['_data.tuple']
            odict['_data'] = {}
            for k in data:
                odict['_data'][k] = BUFFERDICTDATA(slice=data[k][0],
                                                    shape=data[k][1])
        self.__dict__.update(odict)
    ##
    def add(self,k,v=None):
        """ Augment buffer with data ``v``, indexed by key ``k``.
            
        ``v`` is either a scalar or a :mod:`numpy` array (or a list or
        other data type that can be changed into a numpy.array).
        If ``v`` is a :mod:`numpy` array, it can have any shape.
            
        Same as ``self[k] = v`` except: 1) when ``v is None``, in which case k 
        is assumed to be a dictionary and each entry in it is added; and 
        2) when ``k`` is already used in ``self``, in which case a 
        ``ValueError`` is raised.
        """
        if v is None:
            if hasattr(k,'keys'):
                for kk in k:
                    self[kk] = k[kk]
            else:
                for ki,vi in k:
                    self[ki] = vi
        else:
            if k in self:
                raise ValueError("Key %s already used."%k)
            else:
                self[k] = v
    ##
    def __getitem__(self,k):
        """ Return piece of buffer corresponding to key ``k``. """
        if k not in self._data:
            raise KeyError("undefined key: %s" % k)
        if isinstance(self._buf,list):
            self._buf = numpy.array(self._buf)
        d = self._data[k]
        ans = self._buf[d.slice]
        return ans if d.shape is None else ans.reshape(d.shape)
    ##
    def __setitem__(self,k,v):
        """ Set piece of buffer corresponding to ``k`` to value ``v``. 
            
        The shape of ``v`` must equal that of ``self[k]``. If key ``k`` 
        is not in ``self``, use ``self.add(k,v)`` to add it.
        """
        if k not in self:
            v = numpy.asarray(v)
            if v.shape==():
                ## add single piece of data ##
                self._data[k] = BUFFERDICTDATA(slice=len(self._buf),shape=None)
                self._buf = numpy.append(self._buf,v)
                ##
            else:
                ## add array ##
                n = numpy.size(v)
                i = len(self._buf)
                self._data[k] = BUFFERDICTDATA(slice=slice(i,i+n),shape=tuple(v.shape))
                self._buf = numpy.append(self._buf,v)
                ##
            self._keys.append(k)
        else:
            d = self._data[k]
            if d.shape is None:
                try:
                    self._buf[d.slice] = v
                except ValueError:
                    raise ValueError("*** Not a scalar? Shape=%s" 
                                     % str(numpy.shape(v)))
            else:
                v = numpy.asarray(v)
                try:
                    self._buf[d.slice] = v.flat
                except ValueError:
                    raise ValueError("*** Shape mismatch? %s not %s" % 
                                     (str(v.shape),str(d.shape)))
    ##
    def __delitem__(self,k):
        raise NotImplementedError("Cannot delete items from BufferDict.")
    ##
    def __len__(self):
        """ Number of keys. """
        return len(self._keys)
    ##
    def __iter__(self):
        """ Iterator over the keys. """
        return iter(self._keys)
    ##
    def __contains__(self,k):
        """ True if k is a key in ``self``. """
        return k in self._data
    ##
    def __str__(self):
        return str(dict(self.items()))
    ##
    def __repr__(self):
        cn = self.__class__.__name__
        return cn+"("+repr([k for k in self.items()])+")"
    ##
    def _getflat(self):
        return self._buf.flat
    ##
    def _setflat(self,buf):
        """ Replaces buffer with buf if same size. """
        if len(buf)==len(self._buf):
            self._buf = numpy.asarray(buf)
            if self._buf.ndim!=1:
                raise ValueError("Buffer is not 1-d: "+str(self._buf.shape))
        else:
            raise ValueError("Buffer wrong size: %d not %d"
                            %(len(buf),len(self._buf)))
    ##
    flat = property(_getflat,_setflat,doc='Buffer array iterator.')
    def flatten(self):
        """ Copy of buffer array. """
        return numpy.array(self._buf)
    ##
    def _getbuf(self):      # obsolete --- for backwards compatibility
        return self._buf
    ##
    buf = property(_getbuf,_setflat,doc='Similar to flatten(), but reveals real buffer')
    def _getsize(self):
        """ Length of buffer. """
        return len(self._buf)
    ##
    size = property(_getsize,doc='Size of buffer array.')
    def slice(self,k):
        """ Return slice/index in ``self.flat`` corresponding to key ``k``."""
        return self._data[k].slice
    ##
    def isscalar(self,k):
        """ Return ``True`` if ``self[k]`` is scalar else ``False``."""
        return self._data[k].shape is None
    ##
##
##

