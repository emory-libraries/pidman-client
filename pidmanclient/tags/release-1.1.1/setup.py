from setuptools import setup
import pidservices

setup(
    name='pidservices',
    version=pidservices.__version__,
    author=pidservices.__author__,
    author_email=pidservices.__email__,
    packages=['pidservices', 'pidservices.djangowrapper'],
)
