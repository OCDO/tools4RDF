 # Installation

`tools4rdf` can be installed on Linux and Mac OS based systems. On Windows systems, it is recommended to use  [Windows subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install). The following instructions will help install `tools4rdf`:

````{tab-set}
```{tab-item} pip
`pip install tools4rdf`
```

```{tab-item} conda
`conda install -c conda-forge tools4rdf`
```

```{tab-item} from source
We strongly recommend creating a conda environment for the installation. To see how you can install conda see [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/).

Once a conda distribution is available, the following steps will help set up an environment to use `atomrdf`. First step is to clone the repository.

`git clone https://github.com/ocdo/tools4rdf.git`

After cloning, an environment can be created from the included file-

`cd tools4rdf`  
`conda env create -f environment.yml`

This will install the necessary packages and create an environment called rdf. It can be activated by,

`conda activate tools4rdf`

then, install `tools4rdf` using,

`pip install .`
```
````
 