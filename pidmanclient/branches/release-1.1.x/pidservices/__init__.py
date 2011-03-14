"""
*"Nothing can be more hurtful to the service, than the neglect of discipline;
for that discipline, more than numbers, gives one army the superiority over
another."*

- **George Washington**

"""

# Project Version and Author Information
__author__ = "Emory Libraries Software Team"
__copyright__ = "Copyright 2010, Emory University General Library"
__credits__ = ["Scott Turnbull","Rebecca Koeser", "Alex Thomas"]
__email__ = "libsysdev-l@listserv.cc.emory.edu"

# Version Info, parsed below for actual version number.
__version_info__ = (1, 1, 0, 'pre')

# Dot-connect all but the last. Last is dash-connected if not None.
__version__ = '.'.join([ str(i) for i in __version_info__[:-1] ])
if __version_info__[-1] is not None: # Adds dash
    __version__ += ('-%s' % (__version_info__[-1],))
