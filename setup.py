from setuptools import setup, find_packages

setup(
    name='minerva-cli',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'selenium',
    ],
    entry_points={
        'console_scripts': [
            'minerva-cli=minerva_cli.main:main',
        ],
    },
    author='Will Hellinger',
    author_email='your.email@example.com',
    description='A LTHS Latin Automation Tool',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Will-Hellinger/minerva-cli',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)