""" part of lsqfit module: extra functions  """

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

import numpy
import gvar
import lsqfit
from ._utilities import multiminex, gammaQ


def empbayes_fit(z0, fitargs, **minargs): 
    """ Call ``lsqfit.nonlinear_fit(**fitargs(z))`` varying ``z``,
    starting at ``z0``, to maximize ``logGBF`` (empirical Bayes procedure).
        
    The fit is redone for each value of ``z`` that is tried, in order
    to determine ``logGBF``.
        
    :param z0: Starting point for search.
    :type z0: array
    :param fitargs: Function of array ``z`` that determines which fit 
        parameters to use. The function returns these as an argument
        dictionary for :func:`lsqfit.nonlinear_fit`.
    :type fitargs: function
    :param minargs: Optional argument dictionary, passed on to 
        :class:`lsqfit.multiminex`, which finds the minimum.
    :type minargs: dictionary
    :returns: A tuple containing the best fit (object of type 
        :class:`lsqfit.nonlinear_fit`) and the optimal value for parameter ``z``.
    """
    if minargs == {}: # default
        minargs = dict(tol=1e-3, step=math.log(1.1), maxit=30, analyzer=None)
    save = dict(lastz=None, lastp0=None)
    def minfcn(z, save=save):
        args = fitargs(z)
        if save['lastp0'] is not None:
            args['p0'] = save['lastp0']
        fit = lsqfit.nonlinear_fit(**args)
        if numpy.isnan(fit.logGBF):
            raise ValueError
        else:
            save['lastz'] = z 
            save['lastp0'] = fit.pmean
        return -fit.logGBF
    ##
    try:
        z = multiminex(numpy.array(z0), minfcn, **minargs).x
    except ValueError:
        print('*** empbayes_fit warning: null logGBF')
        z = save['lastz']
    args = fitargs(z)
    if save['lastp0'] is not None:
        args['p0'] = save['lastp0']
    return lsqfit.nonlinear_fit(**args), z
##
    
def wavg(xa, svdcut=None, svdnum=None, rescale=True, covfac=None):
    """ Weighted average of 1d-sequence of |GVar|\s or arrays of |GVar|\s.
        
    The weighted average of several |GVar|\s is what one obtains from a 
    least-squares fit of the collection of |GVar|\s to the one-parameter
    fit function ``def f(p): return p[0]``. The average is the best-fit
    value for ``p[0]``. |GVar|\s with smaller standard deviations carry
    more weight than those with larger standard deviations. The averages
    computed by ``wavg`` take account of correlations between the |GVar|\s.
        
    Typical usage is::
        
        x1 = gvar.gvar(...)
        x2 = gvar.gvar(...)
        xavg = wavg([x1, x2])   # weighted average of x1 and x2
        
    In this example, ``x1`` and ``x2`` could be replaced by arrays of 
    |GVar|\s, in which case ``xavg`` is an array as well: for example, ::
        
        x1 = [gvar.gvar(...), gvar.gvar(...)]
        x2 = [gvar.gvar(...), gvar.gvar(...)]
        xavg = wavg([x1, x2])   # xavg[i] is wgtd avg of x1[i] and x2[i]
        
        
    :param xa: The |GVar|\s to be averaged. ``xa`` is a one-dimensional
        sequence of |GVar|\s or of arrays of |GVar|\s, all of the same
        shape.
    :param svdcut: If positive, eigenvalues of the ``xa`` covariance matrix
        that are smaller than ``svdcut`` times the maximum eigenvalue 
        are replaced by ``svdcut`` times the maximum eigenvalue. If 
        negative, eigenmodes with eigenvalues smaller than ``|svdcut|``
        times the largest eigenvalue are discarded. If zero or ``None``,
        the covariance matrix is left unchanged.
    :type svdcut: ``None`` or ``float``
    :param svdnum: If positive, at most ``svdnum`` eigenmodes of the 
        ``xa`` covariance matrix are retained; the modes with the smallest
        eigenvalues are discarded. ``svdnum`` is ignored if set to
        ``None``.
    :type svdnum: ``None`` or ``int``
    :param rescale: If ``True``, rescale covariance matrix so diagonal 
        elements all equal 1 before applying *svd* cuts. (Default is
        ``True``.)
    :type rescale: ``bool``
    :param covfac: The covariance matrix (or matrices) of ``xa`` is 
        multiplied by ``covfac`` if ``covfac`` is not ``None``.
    :type covfac: ``None`` or number
    :returns: Weighted average of the ``xa`` elements. The result has the 
        same type and shape as each element of ``xa`` (that is, either a
        |GVar| or an array of |GVar|\s.)
        
    The following function attributes are also set:    
        
    .. attribute:: wavg.chi2
        
        ``chi**2`` for weighted average.
        
    .. attribute:: wavg.dof
        
        Effective number of degrees of freedom.
        
    .. attribute:: wavg.Q
        
        Quality factor `Q` for fit.
        
    """
    xa = numpy.asarray(xa)
    s = None
    svdcorrection = []
    try:
        ## xa is an array of arrays ##
        shape = xa[0].shape
        xaflat = [xai.flat for xai in xa]
        ans = [wavg(xtuple) for xtuple in zip(*xaflat)]
        ans = numpy.array(ans)
        ans.shape = shape
        return ans
        ##
    except AttributeError:
        pass
    cov = gvar.evalcov(xa)
    if covfac is not None:
        cov *= covfac
    ## invert cov ## 
    if numpy.all(numpy.diag(numpy.diag(cov))==cov):
        ## cov is diagonal ## 
        invcov = 1./numpy.diag(cov)
        dof = len(xa)-1
        ans = numpy.dot(invcov, xa)/sum(invcov)
        chi2 = numpy.sum((xa-ans)**2*invcov).mean
        ##
    else:
        ## cov is not diagonal ##
        if (svdcut is None or svdcut==0) and (svdnum is None or svdnum<0):
            invcov = numpy.linalg.inv(cov)
            dof = len(xa)-1
        else:
            ## apply svdcuts; compute conditioned inverse ## 
            s = gvar.SVD(cov, svdcut=svdcut, svdnum=svdnum, rescale=rescale,
                         compute_delta=True)
            invcov = numpy.sum(numpy.outer(wj, wj) for wj 
                                    in reversed(s.decomp(-1)))
            dof = len(s.val)-1
            if s.delta is not None:
                svdcorrection = sum(s.delta)
            ##
        ##
        sum_invcov = numpy.sum(invcov, axis=1)
        ans = numpy.dot(sum_invcov, xa)/sum(sum_invcov)
        chi2 = numpy.dot((xa-ans), numpy.dot(invcov, (xa-ans))).mean
    ##
    wavg.chi2 = chi2 
    wavg.dof = dof
    wavg.Q = gammaQ(dof/2., chi2/2.)
    wavg.s = s
    wavg.svdcorrection = svdcorrection
    return ans
##

