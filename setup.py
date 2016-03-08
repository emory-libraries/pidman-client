from setuptools import setup
import pidservices

setup(
    name='pidservices',
    version=pidservices.__version__,
    author=pidservices.__author__,
    author_email=pidservices.__email__,
    packages=['pidservices', 'pidservices.djangowrapper'],
    install_requires=[
        'requests',
    ],
    setup_requires=['pytest-runner'],
    scripts=['scripts/allocate_pids',],
    tests_require=['pytest', 'django', 'mock>=1.3.0'],
)
