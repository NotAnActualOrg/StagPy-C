"""Definition of non-processing subcommands."""

from __future__ import annotations

import typing
from dataclasses import fields
from itertools import zip_longest
from math import ceil
from shutil import get_terminal_size
from textwrap import TextWrapper, indent

import loam.tools
import pandas

from . import __version__, conf, phyvars, stagyydata
from ._helpers import baredoc
from .config import CONFIG_FILE

if typing.TYPE_CHECKING:
    from typing import Callable, Iterable, Mapping, Optional, Sequence, Tuple, Union

    from loam.base import Section

    from .datatypes import Varf, Varr, Vart


def info_cmd() -> None:
    """Print basic information about StagYY run.

    Other Parameters:
        conf.info
    """
    sdat = stagyydata.StagyyData()
    lsnap = sdat.snaps[-1]
    lstep = sdat.steps[-1]
    print(f"StagYY run in {sdat.path}")
    if lsnap.geom.threed:
        dimension = "{0.nxtot} x {0.nytot} x {0.nztot}".format(lsnap.geom)
    elif lsnap.geom.twod_xz:
        dimension = "{0.nxtot} x {0.nztot}".format(lsnap.geom)
    else:
        dimension = "{0.nytot} x {0.nztot}".format(lsnap.geom)
    if lsnap.geom.cartesian:
        print("Cartesian", dimension)
    elif lsnap.geom.cylindrical:
        print("Cylindrical", dimension)
    else:
        print("Spherical", dimension)
    print()
    for step in sdat.walk:
        print(f"Step {step.istep}/{lstep.istep}", end="")
        if step.isnap is not None:
            print(f", snapshot {step.isnap}/{lsnap.isnap}")
        else:
            print()
        series = step.timeinfo.loc[list(conf.info.output)]
        if conf.scaling.dimensional:
            series = series.copy()
            dimensions = []
            for var, val in series.iteritems():
                meta = phyvars.TIME.get(var)
                dim = meta.dim if meta is not None else "1"
                if dim == "1":
                    dimensions.append("")
                else:
                    series[var], dim = sdat.scale(val, dim)
                    dimensions.append(dim)
            series = pandas.concat(
                [
                    series,
                    pandas.Series(data=dimensions, index=series.index, name="dim"),
                ],
                axis=1,
            )
        print(indent(series.to_string(header=False), "  "))
        print()


def _pretty_print(
    key_val: Sequence[Tuple[str, str]],
    sep: str = ": ",
    min_col_width: int = 39,
    text_width: Optional[int] = None,
) -> None:
    """Print a iterable of key/values.

    Args:
        key_val: the pairs of section names and text.
        sep: separator between section names and text.
        min_col_width: minimal acceptable column width
        text_width: text width to use. If set to None, will try to infer the
            size of the terminal.
    """
    if text_width is None:
        text_width = get_terminal_size().columns
    if text_width < min_col_width:
        min_col_width = text_width
    ncols = (text_width + 1) // (min_col_width + 1)
    colw = (text_width + 1) // ncols - 1
    ncols = min(ncols, len(key_val))

    wrapper = TextWrapper(width=colw)
    lines = []
    for key, val in key_val:
        if len(key) + len(sep) >= colw // 2:
            wrapper.subsequent_indent = " "
        else:
            wrapper.subsequent_indent = " " * (len(key) + len(sep))
        lines.extend(wrapper.wrap(f"{key}{sep}{val}"))

    chunks = []
    for rem_col in range(ncols, 1, -1):
        isep = ceil(len(lines) / rem_col)
        while isep < len(lines) and lines[isep][0] == " ":
            isep += 1
        chunks.append(lines[:isep])
        lines = lines[isep:]
    chunks.append(lines)
    full_lines = zip_longest(*chunks, fillvalue="")

    fmt = "|".join([f"{{:{colw}}}"] * (ncols - 1))
    fmt += "|{}" if ncols > 1 else "{}"
    print(*(fmt.format(*line) for line in full_lines), sep="\n")


def _layout(
    dict_vars: Mapping[str, Union[Varf, Varr, Vart]],
    dict_vars_extra: Mapping[str, Callable],
) -> None:
    """Print nicely [(var, description)] from phyvars."""
    desc = [(v, m.description) for v, m in dict_vars.items()]
    desc.extend((v, baredoc(m)) for v, m in dict_vars_extra.items())
    _pretty_print(desc, min_col_width=26)


def var_cmd() -> None:
    """Print a list of available variables.

    See :mod:`stagpy.phyvars` where the lists of variables organized by command
    are defined.
    """
    print_all = not any(getattr(conf.var, fld.name) for fld in fields(conf.var))
    if print_all or conf.var.field:
        print("field:")
        _layout(phyvars.FIELD, phyvars.FIELD_EXTRA)
        print()
    if print_all or conf.var.sfield:
        print("surface field:")
        _layout(phyvars.SFIELD, {})
        print()
    if print_all or conf.var.rprof:
        print("rprof:")
        _layout(phyvars.RPROF, phyvars.RPROF_EXTRA)
        print()
    if print_all or conf.var.time:
        print("time:")
        _layout(phyvars.TIME, phyvars.TIME_EXTRA)
        print()
    if print_all or conf.var.refstate:
        print("refstate:")
        _layout(phyvars.REFSTATE, {})
        print()


def version_cmd() -> None:
    """Print StagPy version.

    Use :data:`stagpy.__version__` to obtain the version in a script.
    """
    print(f"stagpy version: {__version__}")


def config_pp(subs: Iterable[str]) -> None:
    """Pretty print of configuration options.

    Args:
        subs: conf sections to print.
    """
    print("(c|f): available only as CLI argument/in the config file", end="\n\n")
    for sub in subs:
        section: Section = getattr(conf, sub)
        hlp_lst = []
        for fld in fields(section):
            opt = fld.name
            entry = section.meta_(opt).entry
            if entry.in_cli ^ entry.in_file:
                opt += " (c)" if entry.in_cli else " (f)"
            hlp_lst.append((opt, entry.doc))
        if hlp_lst:
            print(f"{sub}:")
            _pretty_print(
                hlp_lst, sep=" -- ", text_width=min(get_terminal_size().columns, 100)
            )
            print()


def config_cmd() -> None:
    """Configuration handling.

    Other Parameters:
        conf.config
    """
    if not (
        conf.common.config
        or conf.config.create
        or conf.config.update
        or conf.config.edit
    ):
        config_pp(sec.name for sec in fields(conf))
    loam.tools.config_cmd_handler(conf, conf.config, CONFIG_FILE)
