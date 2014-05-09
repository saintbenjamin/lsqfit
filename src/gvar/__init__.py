""" Correlated gaussian random variables.
    
Objects of type :class:`gvar.GVar` represent gaussian random variables,
which are specified by a mean and standard deviation. They are created
using :func:`gvar.gvar`: for example, ::
    
    >>> x = gvar.gvar(0,3)          # 0 +- 3
    >>> y = gvar.gvar(2,4)          # 2 +- 4
    >>> z = x+y                     # 2 +- 5
    >>> print(z)
    2 +- 5
    >>> print(z.mean)
    2.0
    >>> print(z.sdev)
    5.0
    
This module contains tools for creating and manipulating gaussian random
variables including:
    
    - ``mean(g)`` --- extract means
    
    - ``sdev(g)`` --- extract standard deviations
    
    - ``var(g)`` --- extract variances

    - ``chi2(g1, g2)`` --- ``chi**2`` of ``g1-g2``.
    
    - ``evalcov(g)`` --- compute covariance matrix

    - ``evalcorr(g)`` --- compute correlation matrix
    
    - ``fmt_values(g)`` --- create table of values for printing
    
    - ``fmt_errorbudget(g)`` --- create error-budget table for printing

    - ``fmt_chi2(f)`` --- format chi**2 information in f as string for printing
    
    - class ``BufferDict`` --- ordered dictionary with data buffer
    
    - ``raniter(g,N)`` --- iterator for random numbers
    
    - ``bootstrap_iter(g,N)`` --- bootstrap iterator
    
    - ``svd(g)`` --- SVD modification of covariance matrix
    
    - ``dataset.bin_data(data)`` --- bin random sample data
    
    - ``dataset.avg_data(data)`` --- estimate means of random sample data
    
    - ``dataset.bootstrap_iter(data,N)`` --- bootstrap random sample data
    
    - class ``dataset.Dataset`` --- class for collecting random sample data

There are also sub-modules that implement some standard numerical analysis 
tools for use with |GVar|\s:

    - ``ode`` --- integration of systems of ordinary differential equations

    - ``cspline`` --- cubic splines for 1-d data
    
"""

# Created by G. Peter Lepage (Cornell University) on 2012-05-31.
# Copyright (c) 2012-14 G. Peter Lepage. 
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

import numpy
import sys

from ._gvarcore import *
gvar = GVarFactory()            # order matters for this statement

from ._svec_smat import *
from ._bufferdict import BufferDict, asbufferdict
from ._utilities import *
from ._version import version as __version__

from . import dataset
from . import ode 
from . import cspline

try:
    # use lsqfit's gammaQ if available; otherwise use one in ._utilities
    from lsqfit._utilities import gammaQ
except:
    pass

_GVAR_LIST = []
NULL_GVAR = gvar(0, 0)

def ranseed(seed=None):
    """ Seed random number generators with tuple ``seed``.
        
    Argument ``seed`` is a :class:`tuple` of integers that is used to seed
    the random number generators used by :mod:`numpy` and  
    :mod:`random` (and therefore by :mod:`gvar`). Reusing 
    the same ``seed`` results in the same set of random numbers.

    ``ranseed`` generates its own seed when called without an argument
    or with ``seed=None``. This seed is stored in ``ranseed.seed`` and 
    also returned by the function. The seed can be used to regenerate
    the same set of random numbers at a later time.
        
    :param seed: A tuple of integers. Generates a random tuple if ``None``.
    :type seed: tuple or None
    :returns: The seed.
    """
    if seed is None:
        seed = numpy.random.randint(1, sys.maxint, size=3)
    seed = tuple(seed)
    numpy.random.seed(seed)
    ranseed.seed = seed
    return seed
    
def switch_gvar(cov=None):
    """ Switch :func:`gvar.gvar` to new :class:`gvar.GVarFactory`.
        
    :returns: New :func:`gvar.gvar`.
    """
    global gvar
    _GVAR_LIST.append(gvar)
    gvar = GVarFactory(cov)
    return gvar
##
    
def restore_gvar():
    """ Restore previous :func:`gvar.gvar`.
        
    :returns: Previous :func:`gvar.gvar`.
    """
    global gvar
    try:
        gvar = _GVAR_LIST.pop()
    except IndexError:
        raise RuntimeError("no previous gvar")
    return gvar
##
    
def gvar_factory(cov=None):
    """ Return new function for creating |GVar|\s (to replace 
    :func:`gvar.gvar`). 
        
    If ``cov`` is specified, it is used as the covariance matrix
    for new |GVar|\s created by the function returned by 
    ``gvar_factory(cov)``. Otherwise a new covariance matrix is created
    internally.
    """
    return GVarFactory(cov)
##
            
def asgvar(x):
    """ Return x if it is type |GVar|; otherwise return 'gvar.gvar(x)`."""
    if isinstance(x,GVar):
        return x
    else:
        return gvar(x)
##

def chi2(g1, g2=None, svdcut=1e-15, svdnum=None, nocorr=False, fmt=False):
    """ Compute chi**2 of ``g1-g2``. 

    ``chi**2`` is a measure of whether the multi-dimensional 
    Gaussian distributions ``g1`` and ``g2`` (dictionaries or arrays) 
    agree with each other --- that is, do their means agree 
    within errors for corresponding elements. The probability is high 
    if ``chi2(g1,g2)/chi2.dof`` is of order 1 or smaller.

    Usually ``g1`` and ``g2`` are dictionaries with the same keys,
    where ``g1[k]`` and ``g2[k]`` are |GVar|\s or arrays of 
    |GVar|\s having the same shape. Alternatively ``g1`` and ``g2``
    can be |GVar|\s, or arrays of |GVar|\s having the same shape. 
    
    One of ``g1`` or ``g2`` can contain numbers instead of |GVar|\s,
    in which case ``chi**2`` is a measure of the likelihood that 
    the numbers came from the distribution specified by the other 
    argument. 

    One or the other of ``g1`` or ``g2`` can be missing keys, or missing
    elements from arrays. Only the parts of ``g1`` and ``g2`` that 
    overlap are used. Also setting ``g2=None`` is equivalent to replacing its 
    elements by zeros.

    ``chi**2`` is computed from the inverse of the covariance matrix
    of ``g1-g2``. The matrix inversion can be sensitive to roundoff 
    errors. In such cases, *SVD* cuts can be applied by setting
    parameters ``svdcut`` and ``svdnum``. See the documentation 
    for :class:`gvar.SVD` for information about these parameters.

    The return value is the ``chi**2``. Extra data is stored in 
    ``chi2`` itself:

    .. attribute:: chi2.dof

        Number of degrees of freedom (that is, the number of variables
        compared).

    .. attribute:: chi2.Q

        The probability that the ``chi**2`` could have been larger, 
        by chance, even if ``g1`` and ``g2`` agree. 
        Values smaller than 0.1 or so suggest that they do not
        agree. Also called the *p-value*.

    If argument ``fmt==True``, then a string is returned containing the
    ``chi**2`` per degree of freedom, the number of degrees of freedom, and
    ``Q``.
    """
    # leaving nocorr (turn off correlations) undocumented because I
    #   suspect I will remove it
    if g2 is None:
        diff = BufferDict(g1).buf if hasattr(g1, 'keys') else numpy.asarray(g1).flatten()
    elif hasattr(g1, 'keys') and hasattr(g2, 'keys'):
        # g1 and g2 are dictionaries
        g1 = BufferDict(g1)
        g2 = BufferDict(g2)
        diff = BufferDict()
        keys = set(g1.keys())
        keys = keys.intersection(g2.keys())
        for k in keys:
            g1k = g1[k]
            g2k = g2[k]
            shape = tuple(
                [min(s1,s2) for s1, s2 in zip(numpy.shape(g1k), numpy.shape(g2k))]
                )
            diff[k] = numpy.zeros(shape, object)
            if len(shape) == 0:
                diff[k] = g1k - g2k
            else:
                for i in numpy.ndindex(shape):
                    diff[k][i] = g1k[i] - g2k[i]
        diff = diff.buf
    elif not hasattr(g1, 'keys') and not hasattr(g2, 'keys'):
        # g1 and g2 are arrays or scalars
        g1 = numpy.asarray(g1)
        g2 = numpy.asarray(g2)
        shape = tuple(
            [min(s1,s2) for s1, s2 in zip(numpy.shape(g1), numpy.shape(g2))]
            )
        diff = numpy.zeros(shape, object)
        if len(shape) == 0:
            diff = numpy.array(g1 - g2)
        else:
            for i in numpy.ndindex(shape):
                diff[i] = g1[i] - g2[i]
        diff = diff.flatten()
    else:
        # g1 and g2 are something else
        raise ValueError(
            'cannot compute chi**2 for types ' + str(type(g1)) + ' ' +
            str(type(g2))
            )
    chi2.dof = diff.size
    if chi2.dof == 0:
        chi2.Q = 0
        return 0.0    
    if nocorr:
        # ignore correlations
        ans = numpy.sum(mean(diff) ** 2 / var(diff))
        chi2.dof = len(diff)
        chi2.s = None
    else:
        s = SVD(evalcov(diff), svdcut=svdcut, svdnum=svdnum, rescale=True)
        ans = numpy.sum(numpy.dot(s.decomp(-1), mean(diff))**2)
        chi2.s = s
        chi2.dof = len(s.val)
    chi2.Q = gammaQ(chi2.dof/2., ans/2.)
    chi2.chi2 = ans
    return ans if fmt == False else fmt_chi2(chi2)

def fmt_chi2(f):
    """ Return string containing ``chi**2/dof``, ``dof`` and ``Q`` from ``f``.

    Assumes ``f`` has attributes ``chi2``, ``dof`` and ``Q``. The 
    logarithm of the Bayes factor will also be printed if ``f`` has
    attribute ``logGBF``.
    """
    if hasattr(f, 'logGBF'):
        fmt = "chi2/dof = %.2g [%d]    Q = %.2g    log(GBF) = %.5g"
        chi2_dof = f.chi2 / f.dof if f.dof != 0 else 0
        return fmt % (chi2_dof, f.dof, f.Q, f.logGBF)
    else:
        fmt = "chi2/dof = %.2g [%d]    Q = %.2g"
        chi2_dof = f.chi2 / f.dof if f.dof != 0 else 0
        return fmt % (chi2_dof, f.dof, f.Q)

def svd(g, svdcut=None, compute_inv=False):
    """ Apply svd cuts to collection of |GVar|\s in ``g``. 
        
    ``g`` is an array of |GVar|\s or a dictionary containing |GVar|\s
    and/or arrays of |GVar|\s. When ``svdcut`` is positive, ``svd(g,...)`` 
    returns a copy of ``g`` whose |GVar|\s have been modified 
    to make their covariance matrix less singular than for the 
    original ``g``; the |GVar| means are unchanged.
    This is done using a rescaled *svd* algorithm: 1) the covariance 
    matrix ``cov`` is rescaled by a diagonal matrix ``D`` so that
    ``D.cov.D`` has all its diagonal elements equal to 1; 
    2) eigenvalues ``eig`` of ``D.cov.D`` are replaced by 
    ``max(eig, svdcut * max_eig)``, where ``max_eig`` is the 
    largest eigenvalue, to form a modified ``D.cov.D``; 3) the 
    modified matrix is un-rescaled to create a modified 
    covariance matrix for the new ``g``\s. 

    Covariance matrices are often block diagonal. In such situations, 
    the rescaled *svd* algorithm is applied to each block independently,  
    and one-dimensional blocks are unchanged. This procedure is faster
    and more accurate than applying the cut to the covariance matrix
    as a whole.

    When ``svdcut`` is negative, eigenmodes of the rescaled covariance matrix
    whose eigenvalues are smaller than ``|svdcut| * max_eig`` are dropped
    from the new matrix and the corresponding components of ``g`` are 
    zeroed out (that is, replaced by 0(0)).

    Setting ``compute_inv=True`` causes :func:`svd` to return 
    a tuple ``(gmod, inv_wgts)`` where ``gmod`` is the modified 
    copy of ``g`` and ``inv_wgts`` is a list of index arrays and 
    vectors from which the inverse of the new covariance matrix 
    can be efficiently created: for example, ::

        inv_cov = numpy.zeros((n, n), float)
        for i, w in inv_wgts:
            inv_cov[i] += numpy.outer(w, w)

    sets ``inv_cov`` equal to the inverse of the covariance matrix of 
    the ``gmod``\s. One common use of ``inv_wgts`` is to 
    compute an expectation value ``u.dot(inv_cov.dot(v))`` which
    can be written ::

        result = 0.0
        for i, w in inv_wgts:
            result += u[i].dot(w) * v[i].dot(w)

    where ``result`` is the desired dot product. The sum is over 
    the diagonal blocks of the covariance matrix; the index array ``i``
    in each case specifies the sub-block.
        
    The input parameters are :
        
    :param g: An array of |GVar|\s or a dicitionary whose values are 
        |GVar|\s and/or arrays of |GVar|\s.
    :param svdcut: If positive, replace eigenvalues of the rescaled
        covariance matrix with ``svdcut*(max eigenvalue)``; if negative, 
        discard eigenmodes with eigenvalues smaller than ``svdcut`` times 
        the maximum eigenvalue. Default is ``None``.
    :type svdcut: ``None`` or number ``(|svdcut|<=1)``.
    :param compute_inv: Compute an eigen-representation of inverse of 
        covariance matrix if ``True``. Default value is ``False``.
    :returns: A copy of ``g`` with a covariance matrix modified by 
        (rescaled) *svd* cuts. If ``compute_inv`` is ``True``,
        a tuple ``(g, inv_wgts)`` is returned where ``inv_wgts`` 
        contains information for reconstructing the inverse of the 
        modified covariance matrix.
       
    Data from the *svd* analysis of ``g``'s covariance matrix is stored in
    ``svd`` itself:
    
    .. attribute:: svd.dof 

        Number of independent degrees of freedom left after the 
        *svd* cut. This is the same as the number initially unless
        ``svdcut < 0`` in which case it may be smaller.

    .. attribute:: svd.nmod

        Number of modes whose eignevalue was modified by the 
        *svd* cut.

    .. attribute:: svd.eigen_range
        
        Ratio of the smallest to largest eigenvalue before *svd* cuts are
        applied (but after rescaling).
                  
    .. attribute:: svd.logdet
        
        Logarithm of the determinant of the covariance matrix after *svd*
        cuts are applied (excluding any omitted modes when 
        ``svdcut < 0``).
          
    .. attribute:: svd.correction
        
        Array containing the *svd* corrections that were added to ``g.flat``
        to create the modified ``g``\s.
    """
    # replace g by a copy of g
    if hasattr(g,'keys'):
        g = BufferDict(g)
    else:
        g = numpy.array(g)
    cov = evalcov(g.flat)
    block_idx = find_diagonal_blocks(cov)
    svd.logdet = 0.0
    svd.correction = numpy.zeros(cov.shape[0], object) + gvar(0, 0)
    svd.eigen_range = 1.
    svd.nmod = 0
    inv_wgts = [([], [])] # 1st entry for all 1x1 blocks
    lost_modes = 0
    for idx in block_idx:
        if len(idx) == 1:
            i = idx[0]
            svd.logdet += numpy.log(cov[i, i])
            if compute_inv:
                inv_wgts[0][0].append(i)
                inv_wgts[0][1].append(cov[i, i] ** (-0.5))
        else:
            idxT = idx[:, numpy.newaxis]
            block_cov = cov[idx, idxT]
            s = SVD(block_cov, svdcut=svdcut, rescale=True, compute_delta=True)
            if s.D is not None:
                svd.logdet -= 2 * numpy.sum(numpy.log(di) for di in s.D)
            svd.logdet += numpy.sum(numpy.log(vali) for vali in s.val)
            if s.delta is not None:
                svd.correction[idx] = s.delta 
                g.flat[idx] += s.delta
            else:
                svd.correction[idx] = NULL_GVAR
            if compute_inv:
                inv_wgts.append(
                    (idx, [w for w in s.decomp(-1)[::-1]])
                    )
            if svdcut is not None and svdcut < 0:
                newg = numpy.zeros(len(idx), object)
                for w in s.vec:
                    newg += (w / s.D) * (w.dot(s.D * g.flat[idx])) 
                lost_modes += len(idx) - len(s.vec)
                g.flat[idx] = newg
            if s.eigen_range < svd.eigen_range:
                svd.eigen_range = s.eigen_range
            svd.nmod += s.nmod
    svd.dof = len(g.flat) - lost_modes
    svd.nmod += lost_modes
    svd.blocks = block_idx
    svd.nblocks = len(block_idx)

    # repack into numpy arrays
    if compute_inv:
        tmp = []
        for iw, wgts in inv_wgts:
            tmp.append(
                (numpy.array(iw, numpy.long), numpy.array(wgts, numpy.double))
                )
        inv_wgts = tmp
        return (g, inv_wgts)
    else:
        return g

def find_diagonal_blocks(m):
    """ Find block-diagonal components of matrix m.

    Returns a list of index arrays identifying the blocks. The 1x1
    blocks are listed first.

    Used by svd.
    """
    unassigned_indices = set(range(m.shape[0]))
    non_zero = []
    blocks = []
    for i in range(m.shape[0]):
        non_zero.append(set(m[i].nonzero()[0]))
        non_zero[i].add(i)
        if len(non_zero[i]) == 1:
            # diagonal element
            blocks.append(non_zero[i])
            unassigned_indices.remove(i)
    while unassigned_indices:
        new_block = non_zero[unassigned_indices.pop()]
        for j in unassigned_indices:
            if not new_block.isdisjoint(non_zero[j]):
                new_block.update(non_zero[j])
        unassigned_indices.difference_update(new_block)
        blocks.append(new_block)
    for i in range(len(blocks)):
        blocks[i] = numpy.array(sorted(blocks[i]))
    return blocks
        
## legacy code support ##
fmt_partialsdev = fmt_errorbudget 
##
