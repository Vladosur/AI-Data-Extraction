from setuptools import setup, find_packages

setup(
    name="pdf_extractor",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'pandas',
        'openai',
        'PyMuPDF',
        'Pillow',
        'python-dotenv',
        'xlsxwriter'
    ],
    python_requires='>=3.7',
    description="Un estrattore di testo da PDF",
    author="Il tuo nome",
    author_email="tua@email.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 