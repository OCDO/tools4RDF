from setuptools import setup, find_packages


with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name='tools4rdf',
    version='0.1.0',
    author='Abril Azocar Guzman, Sarath Menon',
    author_email='sarath.menon@pyscal.org',
    description='python tool for working with ontologies and data models',
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(include=['tools4rdf', 'tools4rdf.*']),
    zip_safe=False,
    download_url = 'https://github.com/ocdo/tools4rdf',
    url = 'https://pyscal.org',
    install_requires=['numpy', 'rdflib', 
    'pyyaml', 'graphviz', 'networkx', 
    'pandas'],
    classifiers=[
        'Programming Language :: Python :: 3'
    ],
    include_package_data=True,
)
