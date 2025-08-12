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