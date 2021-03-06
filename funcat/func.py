# -*- coding: utf-8 -*-
#

from functools import reduce

import numpy as np
import talib

from .context import ExecutionContext
from .utils import FormulaException, rolling_window, handle_numpy_warning
from .time_series import (
    MarketDataSeries,
    NumericSeries,
    BoolSeries,
    fit_series,
    get_series,
    get_bars,
    ensure_timeseries,
)


class OneArgumentSeries(NumericSeries):

    @staticmethod
    def func(*args, **kwargs):
        return talib.MA(*args, **kwargs)

    def __init__(self, series, arg):
        if isinstance(series, NumericSeries):
            series = series.series

            try:
                series[series == np.inf] = np.nan
                series = self.func(series, arg)
            except Exception as e:
                raise FormulaException(e)
        super(OneArgumentSeries, self).__init__(series)
        self.extra_create_kwargs["arg"] = arg


class MovingAverageSeries(OneArgumentSeries):
    """http://www.tadoc.org/indicator/MA.htm"""

    @staticmethod
    def func(*args, **kwargs):
        return talib.MA(*args, **kwargs)


class WeightedMovingAverageSeries(OneArgumentSeries):
    """http://www.tadoc.org/indicator/WMA.htm"""

    @staticmethod
    def func(*args, **kwargs):
        return talib.WMA(*args, **kwargs)


class ExponentialMovingAverageSeries(OneArgumentSeries):
    """http://www.fmlabs.com/reference/default.htm?url=ExpMA.htm"""

    @staticmethod
    def func(*args, **kwargs):
        return talib.EMA(*args, **kwargs)


class StdSeries(OneArgumentSeries):
    @staticmethod
    def func(*args, **kwargs):
        return talib.STDDEV(*args, **kwargs)


class TwoArgumentSeries(NumericSeries):
    func = talib.STDDEV

    def __init__(self, series, arg1, arg2):
        if isinstance(series, NumericSeries):
            series = series.series

            try:
                series[series == np.inf] = np.nan
                series = self.func(series, arg1, arg2)
            except Exception as e:
                raise FormulaException(e)
        super(TwoArgumentSeries, self).__init__(series)
        self.extra_create_kwargs["arg1"] = arg1
        self.extra_create_kwargs["arg2"] = arg2


class SMASeries(TwoArgumentSeries):
    """同花顺专用SMA"""

    def func(self, series, n, _):
        results = np.nan_to_num(series).copy()
        # FIXME this is very slow
        for i in range(1, len(series)):
            results[i] = ((n - 1) * results[i - 1] + results[i]) / n
        return results


class SumSeries(NumericSeries):
    """求和"""
    def __init__(self, series, period):
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series[series == np.inf] = 0
                series[series == -np.inf] = 0
                if period == 0:
                    series = np.cumsum(series)
                else:
                    series = talib.SUM(series, period)
            except Exception as e:
                raise FormulaException(e)
        super(SumSeries, self).__init__(series)
        self.extra_create_kwargs["period"] = period


class AbsSeries(NumericSeries):
    def __init__(self, series):
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series[series == np.inf] = 0
                series[series == -np.inf] = 0
                series = np.abs(series)
            except Exception as e:
                raise FormulaException(e)
        super(AbsSeries, self).__init__(series)


class AveDevSeries(NumericSeries):
    def __init__(self, series, period):
        result_series = MovingAverageSeries(series, period).series  # used to store the result
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series[series == np.inf] = 0
                series[series == -np.inf] = 0
                temp_len = len(series)
                for i in np.arange(period - 1, temp_len):
                    temp_start = i - period + 1
                    temp_series = series[temp_start:(i + 1)]
                    temp_avg = np.mean(temp_series)
                    temp_dev = temp_series - temp_avg
                    result_series[i] = np.mean(np.abs(temp_dev))
            except Exception as e:
                raise FormulaException(e)
        super(AveDevSeries, self).__init__(result_series)
        self.extra_create_kwargs["period"] = period


class DmaSeries(NumericSeries):
    def __init__(self, series, weights):
        if isinstance(series, NumericSeries):
            series = series.series
            try:
                series_mean = np.nanmean(series)
                series[series == np.inf] = series_mean
                series[series == -np.inf] = series_mean
                series[np.isnan(series)] = series_mean
                weights_mean = np.nanmean(weights._series)
                weights._series[np.isnan(weights._series)] = weights_mean
            except Exception as e:
                raise FormulaException(e)
        result_series = series  # used to store the result
        for i in range(1, len(series)):
            result_series[i] = (1 - weights._series[i]) * result_series[i - 1] + weights._series[i] * result_series[i]

        super(DmaSeries, self).__init__(result_series)


@handle_numpy_warning
def CrossOver(s1, s2):
    """s1金叉s2
    :param s1:
    :param s2:
    :returns: bool序列
    :rtype: BoolSeries
    """
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    series1, series2 = fit_series(s1.series, s2.series)
    cond1 = series1 > series2
    series1, series2 = fit_series(s1[1].series, s2[1].series)
    cond2 = series1 <= series2  # s1[1].series <= s2[1].series
    cond1, cond2 = fit_series(cond1, cond2)
    s = cond1 & cond2
    return BoolSeries(s)


def Ref(s1, n):
    return s1[n]


@handle_numpy_warning
def minimum(s1, s2):
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    if len(s1) == 0 or len(s2) == 0:
        raise FormulaException("minimum size == 0")
    series1, series2 = fit_series(s1.series, s2.series)
    s = np.minimum(series1, series2)
    return NumericSeries(s)


@handle_numpy_warning
def maximum(s1, s2):
    s1, s2 = ensure_timeseries(s1), ensure_timeseries(s2)
    if len(s1) == 0 or len(s2) == 0:
        raise FormulaException("maximum size == 0")
    series1, series2 = fit_series(s1.series, s2.series)
    s = np.maximum(series1, series2)
    return NumericSeries(s)


@handle_numpy_warning
def count(cond, n):
    # TODO lazy compute
    series = cond.series
    size = len(cond.series) - n
    try:
        result = np.full(size, 0, dtype=np.int)
    except ValueError as e:
        raise FormulaException(e)
    for i in range(size - 1, 0, -1):
        s = series[-n:]
        result[i] = len(s[s == True])
        series = series[:-1]
    return NumericSeries(result)


@handle_numpy_warning
def every(cond, n):
    return count(cond, n) == n


@handle_numpy_warning
def hhv(s, n):
    # TODO lazy compute
    series = s.series
    size = len(s.series) - n
    try:
        result = np.full(size, 0, dtype=np.float64)
    except ValueError as e:
        raise FormulaException(e)

    result = np.max(rolling_window(series, n), 1)

    return NumericSeries(result)


@handle_numpy_warning
def llv(s, n):
    # TODO lazy compute
    series = s.series
    size = len(s.series) - n
    try:
        result = np.full(size, 0, dtype=np.float64)
    except ValueError as e:
        raise FormulaException(e)

    result = np.min(rolling_window(series, n), 1)

    return NumericSeries(result)


@handle_numpy_warning
def iif(condition, true_statement, false_statement):
    series1 = get_series(true_statement)
    series2 = get_series(false_statement)
    cond_series, series1, series2 = fit_series(condition.series, series1, series2)

    series = series2.copy()
    series[cond_series] = series1[cond_series]

    return NumericSeries(series)
