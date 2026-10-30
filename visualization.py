"""AAI551 annual policy comparison figures with explicit units.

Author: Elaine Liu, with AI development assistance.
"""
import matplotlib.pyplot as plt


def plot_runs(runs):
    """Plot named runs on common employment and income axes; return the figure."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for name, frame in runs.items():
        axes[0].plot(frame.year, frame.employment, label=name)
        axes[1].plot(frame.year, frame.income, label=name)
    for ax, label in zip(axes, ('Labor utilization (%)', 'Annual income (thousand USD/model household)')):
        ax.set(xlabel='Model year', ylabel=label)
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    return fig
