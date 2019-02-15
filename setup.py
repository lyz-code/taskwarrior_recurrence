from setuptools import setup

version = '1.1.0'

setup(
    name='taskwarrior_recurrence',
    version=version,
    description='Fix taskwarrior recurrence',
    author='lyz',
    author_email='lyz@riseup.net',
    packages=['taskwarrior_recurrence', ],
    license='GPLv2',
    long_description=open('README.md').read(),
)
