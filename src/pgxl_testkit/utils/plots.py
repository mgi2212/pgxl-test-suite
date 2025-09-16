
import matplotlib.pyplot as plt

def line_plot(x, y, title, xlabel, ylabel, path):
    fig = plt.figure()
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)

def bar_plot(labels, values, title, xlabel, ylabel, path):
    fig = plt.figure()
    plt.bar(labels, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
