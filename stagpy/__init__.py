"""StagPy is a tool to postprocess StagYY output files.

StagPy is both a CLI tool and a powerful Python library. See the
documentation at
http://stagpy.readthedocs.io/en/stable/

If the environment variable STAGPY_NO_CONFIG is set to 'True', StagPy does not
attempt to read any configuration file.

When using the CLI interface, if the environment variable STAGPY_DEBUG is set
to 'True', warnings are issued normally and StagpyError are raised. Otherwise,
warnings are ignored and only a short form of encountered StagpyErrors is
printed.
"""

import importlib
import os
import pathlib
import shutil
import signal
import sys

from pkg_resources import get_distribution, DistributionNotFound
from setuptools_scm import get_version
from loam.manager import ConfigurationManager

from . import config


def _env(var):
    """Return whether var is set to True."""
    return os.getenv(var) == 'True'


DEBUG = _env('STAGPY_DEBUG')


def sigint_handler(*_):
    """Handler of SIGINT signal.

    It is set when you use StagPy as a command line tool to handle gracefully
    keyboard interruption.
    """
    print('\nSo long, and thanks for all the fish.')
    sys.exit()


def _check_config():
    """Create config files as necessary."""
    config.CONFIG_DIR.mkdir(exist_ok=True)
    verfile = config.CONFIG_DIR / '.version'
    uptodate = verfile.is_file() and verfile.read_text() == __version__
    if not uptodate:
        verfile.write_text(__version__)
    if not (uptodate and config.CONFIG_FILE.is_file()):
        conf.create_config_(update=True)
    for stfile in ('stagpy-paper.mplstyle',
                   'stagpy-slides.mplstyle'):
        stfile_conf = config.CONFIG_DIR / stfile
        if not (uptodate and stfile_conf.is_file()):
            stfile_local = pathlib.Path(__file__).parent / stfile
            shutil.copy(str(stfile_local), str(stfile_conf))


def load_mplstyle():
    """Try to load conf.plot.mplstyle matplotlib style."""
    plt = importlib.import_module('matplotlib.pyplot')
    if conf.plot.mplstyle:
        stfile = config.CONFIG_DIR / (conf.plot.mplstyle + '.mplstyle')
        if stfile.is_file():
            conf.plot.mplstyle = str(stfile)
        try:
            plt.style.use(conf.plot.mplstyle)
        except OSError:
            print('Cannot import style {}.'.format(conf.plot.mplstyle),
                  file=sys.stderr)
            conf.plot.mplstyle = ''
    if conf.plot.xkcd:
        plt.xkcd()


if DEBUG:
    print('StagPy runs in DEBUG mode because the environment variable',
          'STAGPY_DEBUG is set to "True"', sep='\n', end='\n\n')
else:
    _PREV_INT = signal.signal(signal.SIGINT, sigint_handler)

try:
    __version__ = get_version(root='..', relative_to=__file__)
except LookupError:
    __version__ = get_distribution('stagpy').version
except (DistributionNotFound, ValueError):
    __version__ = 'unknown'

_CONF_FILES = ([config.CONFIG_FILE, config.CONFIG_LOCAL]
               if not _env('STAGPY_NO_CONFIG') else [])
conf = ConfigurationManager.from_dict_(config.CONF_DEF)
conf.set_config_files_(*_CONF_FILES)
if not _env('STAGPY_NO_CONFIG'):
    _check_config()
PARSING_OUT = conf.read_configs_()

load_mplstyle()

if not DEBUG:
    signal.signal(signal.SIGINT, _PREV_INT)
