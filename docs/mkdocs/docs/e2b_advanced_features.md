# E2B Extension


We provide an option for local E2B Sandbox.



### Local E2B Sandbox Deployment
To achieve our best benchmark results, we recommend using a pre-defined sandbox template that includes the most commonly used Python and apt packages. 

If you prefer not to use a sandbox template, you can disable it by commenting out the line `template=DEFAULT_TEMPLATE_ID,` in `libs/miroflow-tool/src/miroflow/tool/mcp_servers/python_server.py` (line 145).



# Prepare E2B Sandbox (Optional)

> [!TIP]
> We provide a public E2B sandbox template. Follow this step if you want to reproduce the best scores.
>
> For the E2B sandbox service, we recommend setting up a Linux Docker image with a comprehensive set of apt and Python packages pre-installed. Without these pre-installed packages, the agent will need to spend extra steps and context installing them, resulting in reduced token efficiency.
>
> you need to have `npm` install and `docker` running locally.


1. Install `e2b` command line and login:

```shell
## install e2b
npm install -g @e2b/cli
## check that it is available
which e2b 
```

2. Download our pre-configured Dockerfile:
[e2b.Dockerfile](https://github.com/MiroMindAI/MiroFlow/blob/main/docs/e2b.Dockerfile).

```shell
wget https://github.com/MiroMindAI/MiroFlow/blob/main/docs/e2b.Dockerfile
```

3. Run `e2b template build` command [check official doc here](https://e2b.dev/docs/sdk-reference/cli/v1.0.2/template), use `all_pip_apt_pkg` as the name of template.

```shell
## build the template with `docker build` locally
E2B_ACCESS_TOKEN=${your-token}
e2b template build -c "/root/.jupyter/start-up.sh" -n "all_pip_apt_pkg" -d ./e2b.Dockerfile
## check that template is built successfully
E2B_ACCESS_TOKEN=${your-token} e2b template list
```

You can also create your own custom sandbox template for specific use cases by following similar steps. For more information, please refer to the [E2B Docker documentation](https://e2b.dev/docs/sandbox-template).


### E2B Docker 

This document describes the custom E2B Docker environment used by MiroFlow for code execution. The E2B extension provides a sandboxed environment with pre-installed scientific computing libraries, data analysis tools, and other dependencies commonly needed for AI agent tasks.

```bash
# You can use most Debian-based base images
FROM e2bdev/code-interpreter

# Update package list and install Python 3.10 and pip
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies and customize sandbox
RUN python3 -m pip install --no-cache-dir \
    Flask \
    IPython \
    Pillow \
    PyGithub \
    PyMuPDF \
    PyPDF2 \
    arch \
    arm-pyart \
    arxiv \
    ase \
    astropy \
    astroquery \
    awscli \
    beautifulsoup4 \
    biopython \
    boto3 \
    brian2 \
    cairosvg \
    cgt \
    chardet \
    chess \
    cinemagoer \
    clifford \
    contextily \
    control \
    cryptography \
    cvxpy \
    datasets \
    descarteslabs \
    duckduckgo-search \
    edalize \
    english_words \
    ephem \
    esp-docs \
    flask \
    folium \
    geopandas \
    geopy \
    google-search-results \
    googlesearch-python \
    googletrans \
    habanero \
    helics \
    hijri_converter \
    imbalanced-learn \
    inflect \
    isbnlib \
    kaggle \
    lifelines \
    lxml \
    lxml_html_clean \
    mapclassify \
    markdown \
    'matplotlib>=3.8' \
    mendeleev \
    metpy \
    music21 \
    networkx \
    nipype \
    numba \
    'numpy>=2' \
    opencv-python \
    openpyxl \
    'pandas>=2' \
    pandas_datareader \
    parsl \
    pdf2image \
    pdfminer \
    pdfplumber \
    periodictable \
    plotly \
    polars \
    psycopg2-binary \
    pulp \
    pyXSteam \
    pybel \
    pycryptodome \
    pydot \
    pygplates \
    pymatgen \
    pymupdf \
    pypdf2 \
    pypinyin \
    pyscf \
    pytesseract \
    python-docx \
    pytube \
    pywavelets \
    rdflib \
    reportlab \
    requests \
    requests-html \
    scanpy \
    scikit-image \
    scikit-learn \
    scipy \
    scvelo \
    seaborn \
    selenium \
    semanticscholar \
    shap \
    shapely \
    siphon \
    skyfield \
    smbus2 \
    snappy \
    spglib \
    sphinx \
    splink \
    statsmodels \
    stockfish \
    sympy \
    tabulate \
    torch \
    torchvision \
    transformers \
    uncertainpy \
    us \
    virtualenv \
    wbdata \
    webdriver-manager \
    wikipedia-api \
    wolframalpha \
    wordfreq \
    yfinance \
    yt-dlp \
    docx2txt \
    rdkit \
    stockfish \
    yfinance \
    seaborn \
    python-pptx \
    pyaudio \
    pyshp \
    SpeechRecognition \
    waybackpy

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # ── Basic build & Python ───────────────────────────────
    build-essential gfortran cmake pkg-config git curl wget ca-certificates \
    # ── scientific computing ───────────────────────────────────────
    libopenblas-dev liblapack-dev libatlas-base-dev \
    libssl-dev libffi-dev zlib1g-dev \
    # ── image / OpenCV / Pillow ─────────────────────────
    libgl1 libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 \
    libjpeg-dev libpng-dev libwebp-dev libfreetype6-dev libopenjp2-7 liblcms2-dev \
    # ── video / audio ──────────────────────────────────
    ffmpeg libsndfile1 sox portaudio19-dev \
    # ── PDF / doc / OCR ───────────────────────────────
    poppler-utils pdfgrep ghostscript \
    tesseract-ocr tesseract-ocr-deu \
    libxml2-dev libxslt1-dev \
    # ── other tools ───────────────────────────────────────
    imagemagick unlambda stockfish \
    unzip zip tar nano && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
```



---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI