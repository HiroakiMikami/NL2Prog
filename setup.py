from setuptools import setup

requires = ["torch", "pytorch-nlp", "requests", "transpyle", "nltk", "bashlex"]
extras = {
    "test": ["flake8", "autopep8"],
    "colab": ["jupyter", "jupyter-http-over-ws"],
    "visualize": ["graphviz"]
}

setup(
    name="nl2prog",
    install_requires=requires,
    test_requires=extras["test"],
    colab_requires=extras["colab"],
    visualize_requires=extras["visualize"],
    extras_require=extras)
